#!/usr/bin/env python3
"""Train participant-held-out MER-PS physiological folds."""

from __future__ import annotations

import argparse
import json
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
DEFAULT_CACHE_DIR = PROJECT_ROOT / "data" / "feature_cache"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--device", default="auto", help="auto, cpu, cuda, or cuda:N")
    parser.add_argument("--cpu-threads", type=int, default=6)
    parser.add_argument("--fold", type=int, action="append", help="Fold index to train; repeat for multiple folds.")
    parser.add_argument("--epochs", type=int, default=150)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-3)
    parser.add_argument("--hidden-dim", type=int, default=32)
    parser.add_argument("--dropout", type=float, default=0.7)
    parser.add_argument("--contrastive-weight", type=float, default=0.01)
    parser.add_argument("--patience", type=int, default=35)
    parser.add_argument("--warmup-epochs", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--log-every", type=int, default=1)
    parser.add_argument("--no-cache", action="store_true", help="Rebuild the shared feature cache.")
    parser.add_argument("--metrics-json", type=Path, default=None)
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


def get_folds() -> list[dict[str, list[str]]]:
    subjects = [f"test_{index}" for index in range(1, 25)]
    folds = []
    for fold_index in range(5):
        validation = subjects[fold_index::5]
        training = [subject for subject in subjects if subject not in validation]
        folds.append({"train": training, "val": validation})
    return folds


def load_data(
    data_root: Path,
    cache_dir: Path,
    *,
    force: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str]]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    paths = {key: cache_dir / key for key in ("eeg.npy", "fnirs.npy", "y.npy", "subjects.npy")}
    name_candidates = [cache_dir / "names.txt", cache_dir / "subject_names.txt"]
    name_path = next((path for path in name_candidates if path.exists()), name_candidates[0])
    if not force and all(path.exists() for path in paths.values()) and name_path.exists():
        print(f"Loading features from cache: {cache_dir}", flush=True)
        return (
            np.load(paths["eeg.npy"], allow_pickle=False),
            np.load(paths["fnirs.npy"], allow_pickle=False),
            np.load(paths["y.npy"], allow_pickle=False),
            np.load(paths["subjects.npy"], allow_pickle=False),
            name_path.read_text(encoding="utf-8").strip().splitlines(),
        )

    print(f"Extracting features from {data_root}...", flush=True)
    eeg, fnirs, y, subjects, names = load_enhanced_features(data_root, verbose=True)
    for name, array in (("eeg.npy", eeg), ("fnirs.npy", fnirs), ("y.npy", y), ("subjects.npy", subjects)):
        np.save(paths[name], array)
    names_text = "\n".join(names) + "\n"
    for path in name_candidates:
        path.write_text(names_text, encoding="utf-8")
    return eeg, fnirs, y, subjects, names


def train_fold(
    fold_index: int,
    fold: dict[str, list[str]],
    eeg: np.ndarray,
    fnirs: np.ndarray,
    y: np.ndarray,
    subjects: np.ndarray,
    args: argparse.Namespace,
    device: torch.device,
    model_dir: Path,
) -> dict[str, float]:
    set_seed(args.seed + fold_index)
    train_idx = np.flatnonzero(np.isin(subjects, fold["train"]))
    validation_idx = np.flatnonzero(np.isin(subjects, fold["val"]))
    eeg_n, fnirs_n, stats = standardize_features(eeg, fnirs, train_idx)

    config: dict[str, object] = {
        "eeg_nodes": 64,
        "eeg_features": eeg.shape[2],
        "fnirs_nodes": 51,
        "fnirs_features": fnirs.shape[2],
        "hidden_dim": args.hidden_dim,
        "dropout": args.dropout,
    }
    model = MERPSNetV3(**config).to(device)

    def dataset(indices: np.ndarray) -> TensorDataset:
        return TensorDataset(
            torch.from_numpy(np.ascontiguousarray(eeg_n[indices])).float(),
            torch.from_numpy(np.ascontiguousarray(fnirs_n[indices])).float(),
            torch.from_numpy(np.ascontiguousarray(y[indices])).float(),
        )

    train_loader = DataLoader(dataset(train_idx), batch_size=args.batch_size, shuffle=True, drop_last=False)
    validation_loader = DataLoader(dataset(validation_idx), batch_size=args.batch_size, shuffle=False)
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

    print(
        f"Fold {fold_index}: device={device} train={len(train_idx)} validation={len(validation_idx)}",
        flush=True,
    )
    for epoch in range(1, args.epochs + 1):
        model.train()
        train_loss_sum = 0.0
        train_count = 0
        for eeg_batch, fnirs_batch, target in train_loader:
            eeg_batch = eeg_batch.to(device)
            fnirs_batch = fnirs_batch.to(device)
            target = target.to(device)
            optimizer.zero_grad(set_to_none=True)
            prediction, contrastive_loss = model(eeg_batch, fnirs_batch)
            loss = F.mse_loss(prediction, target) + args.contrastive_weight * contrastive_loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
            train_loss_sum += loss.item() * target.size(0)
            train_count += target.size(0)
        scheduler.step()

        model.eval()
        mse_sum = mae_sum = valence_sum = arousal_sum = total = 0.0
        with torch.no_grad():
            for eeg_batch, fnirs_batch, target in validation_loader:
                eeg_batch = eeg_batch.to(device)
                fnirs_batch = fnirs_batch.to(device)
                target = target.to(device)
                prediction, _ = model(eeg_batch, fnirs_batch)
                total += target.numel()
                mse_sum += F.mse_loss(prediction, target, reduction="sum").item()
                prediction_raw = torch.clamp(prediction * 254.0 + 1.0, 1.0, 255.0)
                target_raw = target * 254.0 + 1.0
                mae_sum += torch.abs(prediction_raw - target_raw).sum().item()
                valence_sum += torch.abs(prediction_raw[:, 0] - target_raw[:, 0]).sum().item()
                arousal_sum += torch.abs(prediction_raw[:, 1] - target_raw[:, 1]).sum().item()

        metrics = {
            "mse": mse_sum / max(total, 1),
            "mae": mae_sum / max(total, 1),
            "v_mae": valence_sum / max(total // 2, 1),
            "a_mae": arousal_sum / max(total // 2, 1),
        }
        if epoch == 1 or epoch % max(1, args.log_every) == 0:
            print(
                f"Fold {fold_index} epoch {epoch:3d} | train={train_loss_sum / max(train_count, 1):.6f} "
                f"mse={metrics['mse']:.6f} mae={metrics['mae']:.2f} "
                f"V={metrics['v_mae']:.2f} A={metrics['a_mae']:.2f}",
                flush=True,
            )

        if metrics["mse"] < best_mse:
            best_mse = metrics["mse"]
            best_metrics = metrics
            patience = 0
            model_dir.mkdir(parents=True, exist_ok=True)
            torch.save(
                {
                    "model_state": model.state_dict(),
                    "model_config": config,
                    "standardization": {
                        key: value.tolist() if hasattr(value, "tolist") else value
                        for key, value in stats.items()
                    },
                    "validation": metrics,
                    "training": {
                        "fold": fold_index,
                        "seed": args.seed + fold_index,
                        "epoch": epoch,
                        "training_subjects": fold["train"],
                        "validation_subjects": fold["val"],
                    },
                },
                model_dir / f"fold_{fold_index}_best.pt",
            )
        else:
            patience += 1
        if patience >= args.patience:
            print(f"Fold {fold_index}: early stopping at epoch {epoch}", flush=True)
            break

    if best_metrics is None:
        raise RuntimeError(f"Fold {fold_index} completed without a valid checkpoint")
    print(
        f"Fold {fold_index} best: mse={best_metrics['mse']:.6f} mae={best_metrics['mae']:.2f} "
        f"V={best_metrics['v_mae']:.2f} A={best_metrics['a_mae']:.2f}",
        flush=True,
    )
    return best_metrics


def main() -> None:
    args = parse_args()
    if args.epochs < 1:
        raise ValueError("--epochs must be positive")
    folds_to_train = sorted(set(args.fold if args.fold is not None else range(5)))
    if any(index < 0 or index >= 5 for index in folds_to_train):
        raise ValueError("--fold must be between 0 and 4")

    data_root = resolve_project_path(args.data_root)
    cache_dir = resolve_project_path(args.cache_dir)
    model_dir = resolve_project_path(args.model_dir)
    metrics_path = resolve_project_path(args.metrics_json) if args.metrics_json is not None else None
    torch.set_num_threads(max(1, args.cpu_threads))
    device = select_device(args.device)
    print(f"Device: {device}; folds={folds_to_train}", flush=True)
    print(f"Cache directory: {cache_dir}", flush=True)
    print(f"Model directory: {model_dir}", flush=True)

    eeg, fnirs, y, subjects, _ = load_data(data_root, cache_dir, force=args.no_cache)
    print(f"Feature shapes: EEG={eeg.shape}, fNIRS={fnirs.shape}, targets={y.shape}", flush=True)
    folds = get_folds()
    results: dict[str, dict[str, float]] = {}
    for fold_index in folds_to_train:
        results[str(fold_index)] = train_fold(
            fold_index,
            folds[fold_index],
            eeg,
            fnirs,
            y,
            subjects,
            args,
            device,
            model_dir,
        )

    if metrics_path is not None:
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Metrics: {metrics_path}", flush=True)


if __name__ == "__main__":
    main()
