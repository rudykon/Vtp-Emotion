#!/usr/bin/env python3
"""Evaluate fixed-fusion MAE and post-hoc sources on a local external cohort.

The script keeps external labels outside model inference, evaluates the final
fixed-fusion predictor, and then reports paired results for five prediction
strategies to explain the observed error.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from merps.features import (  # noqa: E402
    _label_matrix,
    _load_mat,
    _video_keys,
    apply_standardization,
    build_prediction_features,
    read_sample_rows,
)
from merps.model import MERPSNetV3  # noqa: E402
from merps.prior import load_label_prior, predict_label_prior  # noqa: E402


DEFAULT_EXTERNAL_ROOT = PROJECT_ROOT / "data" / "download" / "MER_PS_public_evaluation"
DEFAULT_CHECKPOINT_DIR = PROJECT_ROOT / "checkpoints"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "external_evaluation"

VARIANT_ORDER = (
    "global_constant",
    "video_identity",
    "video_time",
    "physiology",
    "fixed_fusion",
)
VARIANT_LABELS = {
    "global_constant": "Global constant",
    "video_identity": "Video identity",
    "video_time": "Video--time prior",
    "physiology": "Physiological branch",
    "fixed_fusion": "Fixed fusion",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-root", type=Path, default=DEFAULT_EXTERNAL_ROOT)
    parser.add_argument("--checkpoint-dir", type=Path, default=DEFAULT_CHECKPOINT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--source-data-dir",
        type=Path,
        default=None,
        help="Optional directory for compact figure source-data CSV files.",
    )
    parser.add_argument("--device", default="auto", help="auto, cpu, cuda, or cuda:N")
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--cpu-threads", type=int, default=4)
    parser.add_argument("--time-bins", type=int, default=10)
    parser.add_argument(
        "--force-physiology",
        action="store_true",
        help="Ignore a compatible cached physiological prediction and recompute it.",
    )
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


def load_targets(path: Path) -> tuple[list[str], np.ndarray]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"sample_id", "valence", "arousal"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"{path} must contain {sorted(required)}")
        sample_ids: list[str] = []
        values: list[tuple[float, float]] = []
        for row in reader:
            sample_ids.append(row["sample_id"].strip())
            values.append((float(row["valence"]), float(row["arousal"])))
    if len(sample_ids) != len(set(sample_ids)):
        raise ValueError("targets.csv contains duplicate sample_id values")
    target = np.asarray(values, dtype=np.float32)
    if target.ndim != 2 or target.shape[1] != 2:
        raise ValueError(f"Unexpected target shape: {target.shape}")
    if not np.isfinite(target).all() or np.any((target < 1.0) | (target > 255.0)):
        raise ValueError("Targets must be finite and remain within [1, 255]")
    return sample_ids, target


def audit_external_data(
    root: Path,
    rows: Sequence[Mapping[str, object]],
    sample_ids: Sequence[str],
    target: np.ndarray,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    if len(rows) != len(sample_ids) or len(rows) != target.shape[0]:
        raise ValueError("Sample rows and targets have different lengths")
    row_ids = [str(row["sample_id"]) for row in rows]
    if row_ids != list(sample_ids):
        raise ValueError("sample_ids.csv and targets.csv are not in identical order")
    if len(row_ids) != len(set(row_ids)):
        raise ValueError("sample_ids.csv contains duplicate sample_id values")

    annotations: dict[str, dict[str, np.ndarray]] = {}
    grouped: dict[tuple[str, int], list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        grouped[(str(row["subject"]), int(row["video"]))].append(index)

    trial_rows: list[dict[str, object]] = []
    annotation_mismatches = 0
    for (subject, video), indices in sorted(grouped.items()):
        timestamps = np.asarray([int(rows[index]["timestamp"]) for index in indices])
        if not np.array_equal(timestamps, np.arange(timestamps.size)):
            raise ValueError(f"Non-contiguous timestamps for {subject}, video {video}")

        if subject not in annotations:
            annotations[subject] = _load_mat(root / "annotations" / f"{subject}_label.mat")
        video_key = f"video_{video}"
        if video_key not in annotations[subject]:
            raise ValueError(f"Missing {video_key} annotation for {subject}")
        label = _label_matrix(annotations[subject][video_key]).T.astype(np.float32)
        if label.shape[0] != len(indices):
            raise ValueError(
                f"Annotation length mismatch for {subject}, video {video}: "
                f"{label.shape[0]} != {len(indices)}"
            )
        annotation_mismatches += int(np.count_nonzero(label != target[indices]))
        trial_target = target[indices]
        trial_rows.append(
            {
                "subject": subject,
                "video": video,
                "samples": len(indices),
                "duration_seconds": int(timestamps[-1]) + 1,
                "valence_mean": float(trial_target[:, 0].mean()),
                "arousal_mean": float(trial_target[:, 1].mean()),
                "valence_std": float(trial_target[:, 0].std()),
                "arousal_std": float(trial_target[:, 1].std()),
            }
        )

    if annotation_mismatches:
        raise ValueError(
            f"targets.csv differs from MAT annotations at {annotation_mismatches} values"
        )

    subjects = sorted({str(row["subject"]) for row in rows})
    videos = sorted({int(row["video"]) for row in rows})
    subject_counts = {
        subject: sum(str(row["subject"]) == subject for row in rows)
        for subject in subjects
    }
    video_counts = {
        str(video): sum(int(row["video"]) == video for row in rows)
        for video in videos
    }
    audit = {
        "samples": len(rows),
        "subjects": subjects,
        "subject_count": len(subjects),
        "videos": videos,
        "video_count": len(videos),
        "trials": len(grouped),
        "label_scale": [float(target.min()), float(target.max())],
        "subject_sample_counts": subject_counts,
        "video_sample_counts": video_counts,
        "annotation_value_mismatches": annotation_mismatches,
    }
    return audit, trial_rows


def construct_stimulus_predictions(
    rows: Sequence[Mapping[str, object]],
    prior: Mapping[str, np.ndarray],
) -> dict[str, np.ndarray]:
    video_time = predict_label_prior(rows, prior)
    global_value = np.asarray(prior["global_values"], dtype=np.float32)
    global_constant = np.broadcast_to(global_value, video_time.shape).copy()

    values = np.asarray(prior["values"], dtype=np.float32)
    lengths = np.asarray(prior["video_lengths"], dtype=np.int64)
    video_medians: dict[int, np.ndarray] = {}
    for video in sorted({int(row["video"]) for row in rows}):
        if video < 0 or video >= values.shape[0] or lengths[video] <= 0:
            video_medians[video] = global_value
        else:
            video_medians[video] = np.median(
                values[video, : int(lengths[video])], axis=0
            ).astype(np.float32)
    video_identity = np.stack(
        [video_medians[int(row["video"])] for row in rows], axis=0
    ).astype(np.float32)
    return {
        "global_constant": global_constant,
        "video_identity": video_identity,
        "video_time": video_time.astype(np.float32),
    }


def checkpoint_paths(checkpoint_dir: Path) -> list[Path]:
    full = checkpoint_dir / "final_v3.pt"
    if not full.exists():
        full = checkpoint_dir / "best_v3.pt"
    paths = [full] + [checkpoint_dir / f"fold_{index}_best.pt" for index in range(5)]
    missing = [path for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing physiological checkpoints: {missing}")
    return paths


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def physiology_cache_signature(
    sample_ids: Sequence[str],
    checkpoints: Sequence[Path],
) -> dict[str, object]:
    sample_digest = hashlib.sha256("\n".join(sample_ids).encode("utf-8")).hexdigest()
    return {
        "sample_count": len(sample_ids),
        "sample_id_sha256": sample_digest,
        "checkpoints": {path.name: file_sha256(path) for path in checkpoints},
    }


def load_cached_physiology(
    output_dir: Path,
    signature: Mapping[str, object],
) -> np.ndarray | None:
    prediction_path = output_dir / "physiology_float.npy"
    metadata_path = output_dir / "physiology_cache.json"
    if not prediction_path.exists() or not metadata_path.exists():
        return None
    cached_signature = json.loads(metadata_path.read_text(encoding="utf-8"))
    if cached_signature != signature:
        return None
    prediction = np.load(prediction_path, allow_pickle=False)
    if prediction.shape != (int(signature["sample_count"]), 2):
        return None
    if not np.isfinite(prediction).all():
        return None
    return prediction.astype(np.float32)


def save_cached_physiology(
    output_dir: Path,
    prediction: np.ndarray,
    signature: Mapping[str, object],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    np.save(output_dir / "physiology_float.npy", np.asarray(prediction, dtype=np.float32))
    (output_dir / "physiology_cache.json").write_text(
        json.dumps(signature, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def predict_physiology(
    external_root: Path,
    rows: list[dict[str, object]],
    checkpoints: Sequence[Path],
    device: torch.device,
    batch_size: int,
) -> np.ndarray:
    _, eeg, fnirs = build_prediction_features(external_root, rows)
    print(f"External feature shapes: EEG={eeg.shape}, fNIRS={fnirs.shape}", flush=True)
    running_sum = np.zeros((len(rows), 2), dtype=np.float64)

    for index, path in enumerate(checkpoints, start=1):
        print(f"Physiological checkpoint {index}/{len(checkpoints)}: {path.name}", flush=True)
        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
        eeg_n, fnirs_n = apply_standardization(
            eeg,
            fnirs,
            checkpoint["standardization"],
        )
        model = MERPSNetV3(**checkpoint["model_config"]).to(device)
        model.load_state_dict(checkpoint["model_state"])
        model.eval()

        cursor = 0
        with torch.no_grad():
            while cursor < len(rows):
                end = min(cursor + batch_size, len(rows))
                eeg_batch = torch.from_numpy(
                    np.ascontiguousarray(eeg_n[cursor:end])
                ).float().to(device)
                fnirs_batch = torch.from_numpy(
                    np.ascontiguousarray(fnirs_n[cursor:end])
                ).float().to(device)
                prediction, _ = model(eeg_batch, fnirs_batch)
                raw = np.clip(
                    prediction.detach().cpu().numpy() * 254.0 + 1.0,
                    1.0,
                    255.0,
                )
                running_sum[cursor:end] += raw
                cursor = end

        del model, eeg_n, fnirs_n
        if device.type == "cuda":
            torch.cuda.empty_cache()

    return (running_sum / float(len(checkpoints))).astype(np.float32)


def round_predictions(prediction: np.ndarray) -> np.ndarray:
    return np.clip(np.rint(np.asarray(prediction)), 1.0, 255.0).astype(np.int16)


def pearson_correlation(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    x_centered = x - x.mean()
    y_centered = y - y.mean()
    denominator = math.sqrt(float(np.sum(x_centered**2) * np.sum(y_centered**2)))
    if denominator <= 0.0:
        return float("nan")
    return float(np.sum(x_centered * y_centered) / denominator)


def concordance_correlation(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    covariance = float(np.mean((x - x.mean()) * (y - y.mean())))
    denominator = float(x.var() + y.var() + (x.mean() - y.mean()) ** 2)
    if denominator <= 0.0:
        return float("nan")
    return float(2.0 * covariance / denominator)


def calculate_metrics(prediction: np.ndarray, target: np.ndarray) -> dict[str, float]:
    prediction = np.asarray(prediction, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)
    difference = prediction - target
    absolute = np.abs(difference)
    return {
        "overall_mae": float(absolute.mean()),
        "valence_mae": float(absolute[:, 0].mean()),
        "arousal_mae": float(absolute[:, 1].mean()),
        "overall_mse": float(np.mean(difference**2)),
        "valence_r": pearson_correlation(prediction[:, 0], target[:, 0]),
        "arousal_r": pearson_correlation(prediction[:, 1], target[:, 1]),
        "valence_ccc": concordance_correlation(prediction[:, 0], target[:, 0]),
        "arousal_ccc": concordance_correlation(prediction[:, 1], target[:, 1]),
    }


def group_metric_rows(
    rows: Sequence[Mapping[str, object]],
    predictions: Mapping[str, np.ndarray],
    target: np.ndarray,
    group_name: str,
    group_values: Sequence[object],
) -> list[dict[str, object]]:
    grouped_indices: dict[object, list[int]] = defaultdict(list)
    for index, value in enumerate(group_values):
        grouped_indices[value].append(index)

    output: list[dict[str, object]] = []
    for group_value, indices in sorted(grouped_indices.items(), key=lambda item: item[0]):
        selection = np.asarray(indices, dtype=np.int64)
        for variant in VARIANT_ORDER:
            output.append(
                {
                    group_name: group_value,
                    "variant": variant,
                    "variant_label": VARIANT_LABELS[variant],
                    "samples": len(indices),
                    **calculate_metrics(predictions[variant][selection], target[selection]),
                }
            )
    return output


def relative_time_bins(
    rows: Sequence[Mapping[str, object]],
    bins: int,
) -> np.ndarray:
    if bins < 2:
        raise ValueError("--time-bins must be at least 2")
    trial_max: dict[tuple[str, int], int] = defaultdict(int)
    for row in rows:
        key = (str(row["subject"]), int(row["video"]))
        trial_max[key] = max(trial_max[key], int(row["timestamp"]))
    output = np.empty(len(rows), dtype=np.int16)
    for index, row in enumerate(rows):
        key = (str(row["subject"]), int(row["video"]))
        duration = trial_max[key] + 1
        value = int(math.floor(int(row["timestamp"]) * bins / max(duration, 1)))
        output[index] = min(max(value, 0), bins - 1)
    return output


def write_csv(path: Path, rows: Iterable[Mapping[str, object]]) -> None:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"No rows available for {path}")
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_prediction_table(
    path: Path,
    rows: Sequence[Mapping[str, object]],
    target: np.ndarray,
    predictions: Mapping[str, np.ndarray],
    time_bins: np.ndarray,
) -> None:
    records = []
    for index, row in enumerate(rows):
        record: dict[str, object] = {
            "sample_id": row["sample_id"],
            "subject": row["subject"],
            "video": row["video"],
            "timestamp": row["timestamp"],
            "relative_time_bin": int(time_bins[index]),
            "target_valence": int(target[index, 0]),
            "target_arousal": int(target[index, 1]),
        }
        for variant in VARIANT_ORDER:
            record[f"{variant}_valence"] = int(predictions[variant][index, 0])
            record[f"{variant}_arousal"] = int(predictions[variant][index, 1])
        records.append(record)
    write_csv(path, records)


def copy_source_data(
    source_dir: Path,
    overall_rows: list[dict[str, object]],
    subject_rows: list[dict[str, object]],
    video_rows: list[dict[str, object]],
    time_rows: list[dict[str, object]],
    trial_rows: list[dict[str, object]],
) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    write_csv(source_dir / "source_data_external_overall.csv", overall_rows)
    write_csv(source_dir / "source_data_external_subject.csv", subject_rows)
    write_csv(source_dir / "source_data_external_video.csv", video_rows)
    write_csv(source_dir / "source_data_external_time.csv", time_rows)
    write_csv(source_dir / "source_data_external_trials.csv", trial_rows)


def main() -> None:
    args = parse_args()
    external_root = resolve_project_path(args.external_root)
    checkpoint_dir = resolve_project_path(args.checkpoint_dir)
    output_dir = resolve_project_path(args.output_dir)
    source_data_dir = (
        resolve_project_path(args.source_data_dir)
        if args.source_data_dir is not None
        else None
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    torch.set_num_threads(max(1, args.cpu_threads))
    device = select_device(args.device)
    print(f"Device: {device}", flush=True)
    print(f"External data root: {external_root}", flush=True)

    rows = read_sample_rows(external_root)
    sample_ids, target = load_targets(external_root / "targets.csv")
    audit, trial_rows = audit_external_data(
        external_root,
        rows,
        sample_ids,
        target,
    )
    (output_dir / "data_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_csv(output_dir / "trial_summary.csv", trial_rows)
    print(
        f"Audit: samples={audit['samples']} subjects={audit['subject_count']} "
        f"videos={audit['video_count']} trials={audit['trials']}",
        flush=True,
    )

    prior = load_label_prior(checkpoint_dir / "label_prior.npz")
    float_predictions = construct_stimulus_predictions(rows, prior)

    checkpoints = checkpoint_paths(checkpoint_dir)
    signature = physiology_cache_signature(sample_ids, checkpoints)
    physiology = None
    if not args.force_physiology:
        physiology = load_cached_physiology(output_dir, signature)
        if physiology is not None:
            print("Using compatible cached physiological prediction.", flush=True)
    if physiology is None:
        physiology = predict_physiology(
            external_root,
            rows,
            checkpoints,
            device,
            args.batch_size,
        )
        save_cached_physiology(output_dir, physiology, signature)

    float_predictions["physiology"] = physiology
    blend_weights = np.asarray(prior.get("blend_weights", [0.99, 0.92]), dtype=np.float32)
    float_predictions["fixed_fusion"] = (
        blend_weights[None, :] * float_predictions["video_time"]
        + (1.0 - blend_weights[None, :]) * physiology
    ).astype(np.float32)
    predictions = {
        variant: round_predictions(float_predictions[variant])
        for variant in VARIANT_ORDER
    }

    overall_rows: list[dict[str, object]] = []
    metrics_json: dict[str, dict[str, float]] = {}
    for variant in VARIANT_ORDER:
        metrics = calculate_metrics(predictions[variant], target)
        metrics_json[variant] = metrics
        overall_rows.append(
            {
                "variant": variant,
                "variant_label": VARIANT_LABELS[variant],
                "samples": len(rows),
                **metrics,
            }
        )
        print(
            f"{VARIANT_LABELS[variant]}: MAE={metrics['overall_mae']:.10f} "
            f"V={metrics['valence_mae']:.10f} A={metrics['arousal_mae']:.10f} "
            f"MSE={metrics['overall_mse']:.10f}",
            flush=True,
        )

    subject_values = [str(row["subject"]) for row in rows]
    video_values = [int(row["video"]) for row in rows]
    time_bins = relative_time_bins(rows, args.time_bins)
    subject_rows = group_metric_rows(
        rows, predictions, target, "subject", subject_values
    )
    video_rows = group_metric_rows(rows, predictions, target, "video", video_values)
    time_rows = group_metric_rows(
        rows,
        predictions,
        target,
        "relative_time_bin",
        [int(value) for value in time_bins],
    )

    write_csv(output_dir / "metrics_overall.csv", overall_rows)
    write_csv(output_dir / "metrics_by_subject.csv", subject_rows)
    write_csv(output_dir / "metrics_by_video.csv", video_rows)
    write_csv(output_dir / "metrics_by_time_bin.csv", time_rows)
    write_prediction_table(
        output_dir / "paired_predictions.csv",
        rows,
        target,
        predictions,
        time_bins,
    )
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics_json, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if source_data_dir is not None:
        copy_source_data(
            source_data_dir,
            overall_rows,
            subject_rows,
            video_rows,
            time_rows,
            trial_rows,
        )
        print(f"Figure source data: {source_data_dir}", flush=True)
    print(f"External evaluation outputs: {output_dir}", flush=True)


if __name__ == "__main__":
    main()
