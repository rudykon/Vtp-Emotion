#!/usr/bin/env python3
"""Train the MER-PS physiological model on a fixed 20/4 participant split."""

from __future__ import annotations

import argparse
import math
import random
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from merps.features import load_enhanced_features, standardize_features
from merps.model import MERPSNetV3

DEFAULT_DATA_ROOT = PROJECT_ROOT / "data" / "MER_PS_trainval"
DEFAULT_MODEL_DIR = PROJECT_ROOT / "checkpoints"
DEFAULT_LOG_PATH = PROJECT_ROOT / "artifacts" / "training_log_v3.txt"
DEFAULT_CACHE_DIR = PROJECT_ROOT / "data" / "feature_cache"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--log-path", type=Path, default=DEFAULT_LOG_PATH)
    parser.add_argument("--device", default="auto", help="auto, cpu, cuda, or cuda:N")
    parser.add_argument("--cpu-threads", type=int, default=8)
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=5e-4)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--dropout", type=float, default=0.5)
    parser.add_argument("--contrastive-weight", type=float, default=0.05)
    parser.add_argument("--patience", type=int, default=30)
    parser.add_argument("--warmup-epochs", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-cache", action="store_true", help="Rebuild the feature cache from raw MAT files.")
    parser.add_argument("--prepare-only", action="store_true", help="Prepare or validate features, then stop before training.")
    parser.add_argument("--test-mode", action="store_true", help="Run a quick three-epoch training check.")
    return parser.parse_args(argv)


def resolve_project_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def select_device(name: str) -> torch.device:
    if name == "auto":
        name = "cuda" if torch.cuda.is_available() else "cpu"
    device = torch.device(name)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available")
    if device.type == "cuda" and device.index is not None:
        torch.cuda.set_device(device)
    return device


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def feature_cache_paths(cache_dir: Path) -> dict[str, Path]:
    return {
        "eeg": cache_dir / "eeg.npy",
        "fnirs": cache_dir / "fnirs.npy",
        "y": cache_dir / "y.npy",
        "subjects": cache_dir / "subjects.npy",
        "subject_names": cache_dir / "subject_names.txt",
        "names": cache_dir / "names.txt",
    }


def load_or_cache_features(
    data_root: Path,
    cache_dir: Path,
    *,
    force: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str]]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    paths = feature_cache_paths(cache_dir)
    name_path = paths["subject_names"] if paths["subject_names"].exists() else paths["names"]
    arrays_ready = all(paths[key].exists() for key in ("eeg", "fnirs", "y", "subjects"))
    if not force and arrays_ready and name_path.exists():
        print(f"Loading features from cache: {cache_dir}", flush=True)
        return (
            np.load(paths["eeg"], allow_pickle=False),
            np.load(paths["fnirs"], allow_pickle=False),
            np.load(paths["y"], allow_pickle=False),
            np.load(paths["subjects"], allow_pickle=False),
            name_path.read_text(encoding="utf-8").strip().splitlines(),
        )

    print(f"Extracting features from {data_root}...", flush=True)
    eeg, fnirs, y, subjects, names = load_enhanced_features(data_root, verbose=True)
    for key, array in (("eeg", eeg), ("fnirs", fnirs), ("y", y), ("subjects", subjects)):
        np.save(paths[key], array)
    names_text = "\n".join(names) + "\n"
    paths["subject_names"].write_text(names_text, encoding="utf-8")
    paths["names"].write_text(names_text, encoding="utf-8")
    print(f"Cached features under {cache_dir}", flush=True)
    return eeg, fnirs, y, subjects, names


def build_model(args: argparse.Namespace, device: torch.device) -> tuple[MERPSNetV3, dict[str, object]]:
    config: dict[str, object] = {
        "eeg_nodes": 64,
        "eeg_features": 45,
        "fnirs_nodes": 51,
        "fnirs_features": 90,
        "output_dim": 2,
        "hidden_dim": args.hidden_dim,
        "heads": 4,
        "dropout": args.dropout,
        "cheb_orders": (1, 2, 3),
    }
    model = MERPSNetV3(**config).to(device)
    print(f"Model parameters: {sum(parameter.numel() for parameter in model.parameters()):,}", flush=True)
    return model, config


def make_loaders(
    eeg: np.ndarray,
    fnirs: np.ndarray,
    y: np.ndarray,
    subjects: np.ndarray,
    train_subjects: list[str],
    validation_subjects: list[str],
    batch_size: int,
) -> tuple[DataLoader, DataLoader, dict[str, np.ndarray]]:
    train_idx = np.flatnonzero(np.isin(subjects, train_subjects))
    validation_idx = np.flatnonzero(np.isin(subjects, validation_subjects))
    eeg_n, fnirs_n, stats = standardize_features(eeg, fnirs, train_idx)
    print(f"Training samples: {len(train_idx)}; validation samples: {len(validation_idx)}", flush=True)

    def dataset(indices: np.ndarray) -> TensorDataset:
        return TensorDataset(
            torch.from_numpy(np.ascontiguousarray(eeg_n[indices])).float(),
            torch.from_numpy(np.ascontiguousarray(fnirs_n[indices])).float(),
            torch.from_numpy(np.ascontiguousarray(y[indices])).float(),
        )

    train_loader = DataLoader(dataset(train_idx), batch_size=batch_size, shuffle=True, drop_last=False)
    validation_loader = DataLoader(dataset(validation_idx), batch_size=batch_size, shuffle=False)
    return train_loader, validation_loader, stats


def train_epoch(
    model: MERPSNetV3,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    contrastive_weight: float,
) -> float:
    model.train()
    total_loss = 0.0
    count = 0
    for eeg, fnirs, target in loader:
        eeg, fnirs, target = eeg.to(device), fnirs.to(device), target.to(device)
        optimizer.zero_grad(set_to_none=True)
        prediction, contrastive_loss = model(eeg, fnirs)
        loss = F.mse_loss(prediction, target) + contrastive_weight * contrastive_loss
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        optimizer.step()
        batch_size = target.size(0)
        total_loss += loss.item() * batch_size
        count += batch_size
    return total_loss / max(count, 1)


@torch.no_grad()
def evaluate_model(model: MERPSNetV3, loader: DataLoader, device: torch.device) -> dict[str, float]:
    model.eval()
    mse_sum = mae_sum = valence_sum = arousal_sum = total = 0.0
    for eeg, fnirs, target in loader:
        eeg, fnirs, target = eeg.to(device), fnirs.to(device), target.to(device)
        prediction, _ = model(eeg, fnirs)
        numel = target.numel()
        total += numel
        mse_sum += F.mse_loss(prediction, target, reduction="sum").item()
        prediction_raw = torch.clamp(prediction * 254.0 + 1.0, 1.0, 255.0)
        target_raw = target * 254.0 + 1.0
        mae_sum += torch.abs(prediction_raw - target_raw).sum().item()
        valence_sum += torch.abs(prediction_raw[:, 0] - target_raw[:, 0]).sum().item()
        arousal_sum += torch.abs(prediction_raw[:, 1] - target_raw[:, 1]).sum().item()
    return {
        "mse": mse_sum / max(total, 1),
        "mae": mae_sum / max(total, 1),
        "v_mae": valence_sum / max(total // 2, 1),
        "a_mae": arousal_sum / max(total // 2, 1),
    }


def save_checkpoint(
    path: Path,
    model: MERPSNetV3,
    config: dict[str, object],
    stats: dict[str, np.ndarray],
    validation: dict[str, float],
    training: dict[str, object],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state": model.state_dict(),
            "model_config": config,
            "standardization": {
                key: value.tolist() if hasattr(value, "tolist") else value
                for key, value in stats.items()
            },
            "validation": validation,
            "training": training,
        },
        path,
    )


def main() -> None:
    args = parse_args()
    if args.test_mode:
        args.epochs = 3
        args.batch_size = 64
    if args.epochs < 1 and not args.prepare_only:
        raise ValueError("--epochs must be positive")

    data_root = resolve_project_path(args.data_root)
    cache_dir = resolve_project_path(args.cache_dir)
    model_dir = resolve_project_path(args.model_dir)
    log_path = resolve_project_path(args.log_path)
    torch.set_num_threads(max(1, args.cpu_threads))
    set_seed(args.seed)
    device = select_device(args.device)
    print(f"Device: {device}", flush=True)
    print(f"Data root: {data_root}", flush=True)
    print(f"Cache directory: {cache_dir}", flush=True)
    print(f"Model directory: {model_dir}", flush=True)

    eeg, fnirs, y, subjects, _ = load_or_cache_features(
        data_root,
        cache_dir,
        force=args.no_cache,
    )
    print(f"Feature shapes: EEG={eeg.shape}, fNIRS={fnirs.shape}, targets={y.shape}", flush=True)
    if args.prepare_only:
        print("Feature preparation completed; training was not requested.", flush=True)
        return

    train_subjects = [f"test_{index}" for index in range(1, 21)]
    validation_subjects = [f"test_{index}" for index in range(21, 25)]
    train_loader, validation_loader, stats = make_loaders(
        eeg,
        fnirs,
        y,
        subjects,
        train_subjects,
        validation_subjects,
        args.batch_size,
    )
    model, config = build_model(args, device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)

    def lr_lambda(epoch: int) -> float:
        if epoch < args.warmup_epochs:
            return (epoch + 1) / max(args.warmup_epochs, 1)
        progress = (epoch - args.warmup_epochs) / max(1, args.epochs - args.warmup_epochs)
        return 0.5 * (1.0 + math.cos(math.pi * progress))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)
    best_mse = float("inf")
    best_metrics: dict[str, float] | None = None
    patience = 0
    epochs_run = 0

    for epoch in range(1, args.epochs + 1):
        epochs_run = epoch
        train_loss = train_epoch(model, train_loader, optimizer, device, args.contrastive_weight)
        validation = evaluate_model(model, validation_loader, device)
        scheduler.step()
        print(
            f"epoch {epoch:3d} | train={train_loss:.6f} | mse={validation['mse']:.6f} "
            f"mae={validation['mae']:.2f} (V:{validation['v_mae']:.2f} A:{validation['a_mae']:.2f}) "
            f"| lr={scheduler.get_last_lr()[0]:.2e}",
            flush=True,
        )

        if validation["mse"] < best_mse:
            best_mse = validation["mse"]
            best_metrics = validation
            patience = 0
            save_checkpoint(
                model_dir / "best_v3.pt",
                model,
                config,
                stats,
                validation,
                {
                    "split": "participants_1_20_train_21_24_validation",
                    "seed": args.seed,
                    "epoch": epoch,
                },
            )
        else:
            patience += 1
        if patience >= args.patience:
            print(f"Early stopping at epoch {epoch}", flush=True)
            break

    if best_metrics is None:
        raise RuntimeError("Training completed without a valid checkpoint")
    print(
        f"Best validation: mse={best_metrics['mse']:.6f} mae={best_metrics['mae']:.2f} "
        f"V={best_metrics['v_mae']:.2f} A={best_metrics['a_mae']:.2f}",
        flush=True,
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        f"epochs_run={epochs_run}\n"
        f"mse={best_metrics['mse']:.6f}\n"
        f"mae={best_metrics['mae']:.6f}\n"
        f"valence_mae={best_metrics['v_mae']:.6f}\n"
        f"arousal_mae={best_metrics['a_mae']:.6f}\n",
        encoding="utf-8",
    )
    print(f"Training log: {log_path}", flush=True)


if __name__ == "__main__":
    main()
