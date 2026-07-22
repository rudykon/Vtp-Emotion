from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np

from .features import _label_matrix, _load_mat, _video_keys, discover_subjects


DEFAULT_BLEND_WEIGHTS = np.asarray([0.99, 0.92], dtype=np.float32)
DEFAULT_SMOOTH_RADIUS = 3


def build_label_prior(
    data_root: str | Path,
    subjects: Iterable[str] | None = None,
    smooth_radius: int = DEFAULT_SMOOTH_RADIUS,
    reducer: str = "median",
    blend_weights: Sequence[float] = DEFAULT_BLEND_WEIGHTS,
) -> dict[str, np.ndarray]:
    data_root = Path(data_root)
    subject_names = list(subjects) if subjects is not None else discover_subjects(data_root)
    if not subject_names:
        raise ValueError(f"No subjects found under {data_root / 'data'}")
    if reducer not in {"median", "mean"}:
        raise ValueError("reducer must be 'median' or 'mean'")

    labels_by_video: dict[int, list[np.ndarray]] = {}
    all_labels: list[np.ndarray] = []
    for subject in subject_names:
        labels = _load_mat(data_root / "annotations" / f"{subject}_label.mat")
        for video_key in _video_keys(labels):
            video_id = int(video_key.split("_", 1)[1])
            label = _label_matrix(labels[video_key]).T.astype(np.float32)
            labels_by_video.setdefault(video_id, []).append(label)
            all_labels.append(label)

    if not labels_by_video:
        raise ValueError(f"No label trajectories found under {data_root / 'annotations'}")

    max_video = max(labels_by_video)
    max_length = max(label.shape[0] for labels in labels_by_video.values() for label in labels)
    values = np.full((max_video + 1, max_length, 2), np.nan, dtype=np.float32)
    video_lengths = np.zeros(max_video + 1, dtype=np.int16)

    reduce_fn = np.median if reducer == "median" else np.mean
    for video_id, video_labels in sorted(labels_by_video.items()):
        trajectory = _reduce_variable_length(video_labels, reduce_fn)
        if smooth_radius > 0:
            trajectory = _smooth_trajectory(trajectory, smooth_radius)
        n = trajectory.shape[0]
        values[video_id, :n] = trajectory
        video_lengths[video_id] = n

    global_values = reduce_fn(np.concatenate(all_labels, axis=0), axis=0).astype(np.float32)
    return {
        "values": np.clip(values, 1.0, 255.0).astype(np.float32),
        "video_lengths": video_lengths,
        "global_values": np.clip(global_values, 1.0, 255.0).astype(np.float32),
        "blend_weights": np.asarray(blend_weights, dtype=np.float32),
        "smooth_radius": np.asarray(smooth_radius, dtype=np.int16),
        "reducer": np.asarray(reducer),
        "subjects": np.asarray(subject_names),
    }


def save_label_prior(path: str | Path, prior: Mapping[str, np.ndarray]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **prior)


def load_label_prior(path: str | Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key] for key in data.files}


def predict_label_prior(
    rows: Sequence[Mapping[str, object]],
    prior: Mapping[str, np.ndarray],
) -> np.ndarray:
    values = np.asarray(prior["values"], dtype=np.float32)
    lengths = np.asarray(prior["video_lengths"], dtype=np.int64)
    fallback = np.asarray(prior["global_values"], dtype=np.float32)

    predictions = np.empty((len(rows), 2), dtype=np.float32)
    for idx, row in enumerate(rows):
        video_id = int(row["video"])
        timestamp = int(row["timestamp"])
        if 0 <= video_id < values.shape[0] and lengths[video_id] > 0:
            clipped_timestamp = min(max(timestamp, 0), int(lengths[video_id]) - 1)
            predictions[idx] = values[video_id, clipped_timestamp]
        else:
            predictions[idx] = fallback
    return np.clip(predictions, 1.0, 255.0)


def build_and_save_prior(
    data_root: str | Path,
    output_path: str | Path,
    smooth_radius: int = DEFAULT_SMOOTH_RADIUS,
    reducer: str = "median",
    blend_weights: Sequence[float] = DEFAULT_BLEND_WEIGHTS,
) -> None:
    prior = build_label_prior(
        data_root=data_root,
        smooth_radius=smooth_radius,
        reducer=reducer,
        blend_weights=blend_weights,
    )
    save_label_prior(output_path, prior)


def _reduce_variable_length(labels: Sequence[np.ndarray], reduce_fn) -> np.ndarray:
    max_length = max(label.shape[0] for label in labels)
    trajectory = np.empty((max_length, 2), dtype=np.float32)
    for timestamp in range(max_length):
        available = [label[timestamp] for label in labels if timestamp < label.shape[0]]
        trajectory[timestamp] = reduce_fn(np.stack(available, axis=0), axis=0)
    return trajectory


def _smooth_trajectory(trajectory: np.ndarray, radius: int) -> np.ndarray:
    smoothed = np.empty_like(trajectory)
    for idx in range(trajectory.shape[0]):
        start = max(0, idx - radius)
        end = min(trajectory.shape[0], idx + radius + 1)
        smoothed[idx] = trajectory[start:end].mean(axis=0)
    return smoothed


def main() -> None:
    parser = argparse.ArgumentParser(description="Build MER-PS video-time label prior.")
    parser.add_argument(
        "--data-root",
        default=Path(__file__).resolve().parents[2] / "data" / "MER_PS_trainval",
    )
    parser.add_argument(
        "--output",
        default=Path(__file__).resolve().parents[2] / "checkpoints" / "label_prior.npz",
    )
    parser.add_argument("--smooth-radius", type=int, default=DEFAULT_SMOOTH_RADIUS)
    parser.add_argument("--reducer", choices=("median", "mean"), default="median")
    parser.add_argument("--valence-prior-weight", type=float, default=float(DEFAULT_BLEND_WEIGHTS[0]))
    parser.add_argument("--arousal-prior-weight", type=float, default=float(DEFAULT_BLEND_WEIGHTS[1]))
    args = parser.parse_args()

    build_and_save_prior(
        data_root=args.data_root,
        output_path=args.output,
        smooth_radius=args.smooth_radius,
        reducer=args.reducer,
        blend_weights=(args.valence_prior_weight, args.arousal_prior_weight),
    )
    print(f"Saved label prior to {args.output}")


if __name__ == "__main__":
    main()
