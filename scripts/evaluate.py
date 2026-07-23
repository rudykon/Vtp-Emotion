from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import torch

from merps.features import _label_matrix, _load_mat, _video_keys, apply_standardization
from merps.model import MERPSNetV3
from merps.prior import (
    DEFAULT_BLEND_WEIGHTS,
    DEFAULT_SMOOTH_RADIUS,
    build_label_prior,
    predict_label_prior,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = PROJECT_ROOT / "data" / "MER_PS_trainval"
DEFAULT_CACHE_DIR = PROJECT_ROOT / "data" / "feature_cache"
DEFAULT_MODEL_DIR = PROJECT_ROOT / "checkpoints"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate fixed-fusion MAE and source contributions under subject-held-out folds.")
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--device", default="auto", help="auto, cpu, cuda, or cuda:N")
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--smooth-radius", type=int, default=DEFAULT_SMOOTH_RADIUS)
    parser.add_argument("--blend-checkpoints", action="store_true")
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--source-data-csv", type=Path, default=None)
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


def main() -> None:
    args = parse_args()
    data_root = resolve_project_path(args.data_root)
    cache_dir = resolve_project_path(args.cache_dir)
    model_dir = resolve_project_path(args.model_dir)
    output_json = resolve_project_path(args.output_json) if args.output_json is not None else None
    source_data_csv = resolve_project_path(args.source_data_csv) if args.source_data_csv is not None else None
    device = select_device(args.device)

    rows, targets_all, subjects = load_label_rows(data_root)
    folds = make_folds()
    prior_predictions = []
    fold_targets = []
    fold_indices = []
    fold_prior_metrics: dict[str, dict[str, float]] = {}
    for fold_index, (training_subjects, validation_subjects) in enumerate(folds):
        validation_idx = np.flatnonzero(np.isin(subjects, validation_subjects))
        fold_indices.append(validation_idx)
        prior = build_label_prior(
            data_root,
            subjects=training_subjects,
            smooth_radius=args.smooth_radius,
            reducer="median",
            blend_weights=DEFAULT_BLEND_WEIGHTS,
        )
        prediction = predict_label_prior([rows[index] for index in validation_idx], prior)
        prior_predictions.append(prediction)
        fold_targets.append(targets_all[validation_idx])
        fold_prior_metrics[str(fold_index)] = print_metrics(
            f"fold {fold_index} prior",
            prediction,
            targets_all[validation_idx],
        )

    prior_all = np.concatenate(prior_predictions, axis=0)
    target_all = np.concatenate(fold_targets, axis=0)
    components: dict[str, dict[str, float]] = {
        "Video--time prior": print_metrics("5-fold prior", prior_all, target_all)
    }

    if args.blend_checkpoints:
        physiology_all = predict_fold_checkpoints(
            fold_indices,
            cache_dir,
            model_dir,
            device,
            args.batch_size,
        )
        weights = DEFAULT_BLEND_WEIGHTS[None, :]
        fusion_all = weights * prior_all + (1.0 - weights) * physiology_all
        components["Physiological branch"] = print_metrics(
            "5-fold physiology",
            physiology_all,
            target_all,
        )
        components["Fused prediction"] = print_metrics(
            "5-fold fixed fusion",
            fusion_all,
            target_all,
        )
        physiology_mae = components["Physiological branch"]["overall_mae"]
        fusion_mae = components["Fused prediction"]["overall_mae"]
        print(
            f"relative_mae_reduction_vs_physiology="
            f"{(physiology_mae - fusion_mae) / physiology_mae * 100.0:.2f}%"
        )
    elif source_data_csv is not None:
        raise ValueError("--source-data-csv requires --blend-checkpoints")

    report = {
        "configuration": {
            "data_root": str(data_root),
            "cache_dir": str(cache_dir),
            "model_dir": str(model_dir),
            "smooth_radius": args.smooth_radius,
            "blend_weights": DEFAULT_BLEND_WEIGHTS.tolist(),
        },
        "fold_prior_metrics": fold_prior_metrics,
        "components": components,
    }
    if output_json is not None:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Evaluation JSON: {output_json}")
    if source_data_csv is not None:
        write_source_data(source_data_csv, components)
        print(f"Figure source data: {source_data_csv}")


def load_label_rows(data_root: Path) -> tuple[list[dict[str, object]], np.ndarray, np.ndarray]:
    rows: list[dict[str, object]] = []
    targets: list[np.ndarray] = []
    subject_values: list[str] = []
    for subject_index in range(1, 25):
        subject = f"test_{subject_index}"
        labels = _load_mat(data_root / "annotations" / f"{subject}_label.mat")
        for video_key in _video_keys(labels):
            video = int(video_key.split("_", 1)[1])
            target = _label_matrix(labels[video_key]).T.astype(np.float32)
            for timestamp in range(target.shape[0]):
                rows.append(
                    {
                        "sample_id": f"{subject}_V{video:02d}_T{timestamp:03d}",
                        "subject": subject,
                        "video": video,
                        "timestamp": timestamp,
                    }
                )
            targets.append(target)
            subject_values.extend([subject] * target.shape[0])
    return rows, np.concatenate(targets, axis=0), np.asarray(subject_values)


def make_folds() -> list[tuple[list[str], list[str]]]:
    subjects = [f"test_{index}" for index in range(1, 25)]
    folds = []
    for fold_index in range(5):
        validation_subjects = subjects[fold_index::5]
        training_subjects = [subject for subject in subjects if subject not in validation_subjects]
        folds.append((training_subjects, validation_subjects))
    return folds


def predict_fold_checkpoints(
    fold_indices: list[np.ndarray],
    cache_dir: Path,
    model_dir: Path,
    device: torch.device,
    batch_size: int,
) -> np.ndarray:
    eeg = np.load(cache_dir / "eeg.npy", allow_pickle=False)
    fnirs = np.load(cache_dir / "fnirs.npy", allow_pickle=False)
    predictions = []
    for fold_index, indices in enumerate(fold_indices):
        checkpoint = torch.load(
            model_dir / f"fold_{fold_index}_best.pt",
            map_location="cpu",
            weights_only=True,
        )
        eeg_n, fnirs_n = apply_standardization(eeg[indices], fnirs[indices], checkpoint["standardization"])
        model = MERPSNetV3(**checkpoint["model_config"]).to(device)
        model.load_state_dict(checkpoint["model_state"])
        model.eval()
        fold_predictions = []
        with torch.no_grad():
            for start in range(0, len(indices), batch_size):
                end = min(start + batch_size, len(indices))
                eeg_batch = torch.from_numpy(np.ascontiguousarray(eeg_n[start:end])).float().to(device)
                fnirs_batch = torch.from_numpy(np.ascontiguousarray(fnirs_n[start:end])).float().to(device)
                prediction, _ = model(eeg_batch, fnirs_batch)
                fold_predictions.append(
                    np.clip(prediction.cpu().numpy() * 254.0 + 1.0, 1.0, 255.0)
                )
        predictions.append(np.concatenate(fold_predictions, axis=0))
    return np.concatenate(predictions, axis=0).astype(np.float32)


def print_metrics(name: str, prediction: np.ndarray, target: np.ndarray) -> dict[str, float]:
    error = np.abs(np.asarray(prediction, dtype=np.float32) - np.asarray(target, dtype=np.float32))
    metrics = {
        "overall_mae": float(error.mean()),
        "valence_mae": float(error[:, 0].mean()),
        "arousal_mae": float(error[:, 1].mean()),
    }
    print(
        f"{name}: mae={metrics['overall_mae']:.6f} "
        f"V_mae={metrics['valence_mae']:.6f} A_mae={metrics['arousal_mae']:.6f}"
    )
    return metrics


def write_source_data(path: Path, components: dict[str, dict[str, float]]) -> None:
    order = ("Physiological branch", "Video--time prior", "Fused prediction")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["component", "Overall", "Valence", "Arousal"])
        writer.writeheader()
        for component in order:
            metrics = components[component]
            writer.writerow(
                {
                    "component": component,
                    "Overall": f"{metrics['overall_mae']:.6f}",
                    "Valence": f"{metrics['valence_mae']:.6f}",
                    "Arousal": f"{metrics['arousal_mae']:.6f}",
                }
            )


if __name__ == "__main__":
    main()
