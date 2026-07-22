from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

from .features import (
    _append_second_context,
    _eeg_features_by_second,
    _fnirs_features_by_second,
    _load_mat,
)


NEUTRAL_LABEL = 128.0


BaselineShrink = float | Sequence[float] | np.ndarray


def normalize_baseline_bias_shrink(shrink: BaselineShrink) -> np.ndarray:
    values = np.asarray(shrink, dtype=np.float32)
    if values.ndim == 0:
        return np.full((2,), float(values.item()), dtype=np.float32)
    if values.shape != (2,):
        raise ValueError(
            f"baseline shrink must be a scalar or shape (2,), got {values.shape}"
        )
    return values.astype(np.float32, copy=True)


def baseline_bias_array(
    rows: Sequence[Mapping[str, object]],
    bias_by_key: Mapping[tuple[str, int | None], np.ndarray],
) -> np.ndarray:
    values = np.zeros((len(rows), 2), dtype=np.float32)
    for index, row in enumerate(rows):
        subject = str(row["subject"])
        video = int(row["video"])
        bias = bias_by_key.get((subject, video))
        if bias is None:
            bias = bias_by_key.get((subject, None))
        if bias is None:
            continue
        bias_value = np.asarray(bias, dtype=np.float32)
        if bias_value.shape != (2,):
            raise ValueError(f"baseline bias must have shape (2,), got {bias_value.shape}")
        values[index] = bias_value
    return values


def apply_baseline_bias_array(
    model_prediction: np.ndarray,
    bias: np.ndarray,
    shrink: BaselineShrink,
) -> np.ndarray:
    model = np.asarray(model_prediction, dtype=np.float32)
    bias_value = np.asarray(bias, dtype=np.float32)
    if model.ndim != 2 or model.shape[1] != 2:
        raise ValueError(f"Expected model_prediction with shape [samples, 2], got {model.shape}")
    if bias_value.shape != model.shape:
        raise ValueError(f"bias shape {bias_value.shape} does not match model shape {model.shape}")
    alpha = normalize_baseline_bias_shrink(shrink)
    corrected = model - bias_value * alpha[None, :]
    return np.clip(corrected, 1.0, 255.0).astype(np.float32)


def aggregate_baseline_bias(
    rows: Sequence[Mapping[str, object]],
    baseline_prediction_by_trial: Mapping[tuple[str, int], np.ndarray],
    mode: str = "subject",
    neutral_label: float = NEUTRAL_LABEL,
) -> dict[tuple[str, int | None], np.ndarray]:
    unique_keys = sorted({(str(row["subject"]), int(row["video"])) for row in rows})
    if mode == "trial":
        return {
            key: (np.asarray(baseline_prediction_by_trial[key], dtype=np.float32) - float(neutral_label)).astype(np.float32)
            for key in unique_keys
            if key in baseline_prediction_by_trial
        }
    if mode != "subject":
        raise ValueError("mode must be 'subject' or 'trial'")

    grouped: dict[str, list[np.ndarray]] = {}
    for key in unique_keys:
        if key in baseline_prediction_by_trial:
            grouped.setdefault(key[0], []).append(np.asarray(baseline_prediction_by_trial[key], dtype=np.float32))
    return {
        (subject, None): (np.mean(np.stack(values, axis=0), axis=0) - float(neutral_label)).astype(np.float32)
        for subject, values in grouped.items()
        if values
    }


def apply_baseline_bias_correction(
    rows: Sequence[Mapping[str, object]],
    model_prediction: np.ndarray,
    bias_by_key: Mapping[tuple[str, int | None], np.ndarray],
    shrink: BaselineShrink,
) -> np.ndarray:
    bias = baseline_bias_array(rows, bias_by_key)
    return apply_baseline_bias_array(model_prediction, bias, shrink)


def build_baseline_prediction_features(
    input_dir: str | Path,
    rows: Sequence[Mapping[str, object]],
) -> tuple[list[tuple[str, int]], np.ndarray, np.ndarray]:
    input_dir = Path(input_dir)
    keys = sorted({(str(row["subject"]), int(row["video"])) for row in rows})
    if not keys:
        return [], np.empty((0, 64, 45), dtype=np.float32), np.empty((0, 51, 90), dtype=np.float32)

    eeg_parts: list[np.ndarray] = []
    fnirs_parts: list[np.ndarray] = []
    expanded_keys: list[tuple[str, int]] = []
    for subject in sorted({subject for subject, _ in keys}):
        subject_dir = input_dir / "data" / subject
        eeg_baselines = _load_mat(subject_dir / "EEG_baselines.mat")
        fnirs_baselines = _load_mat(subject_dir / "fNIRS_baselines.mat")
        for _, video in [key for key in keys if key[0] == subject]:
            video_key = f"video_{video}"
            if video_key not in eeg_baselines or video_key not in fnirs_baselines:
                continue
            eeg = np.asarray(eeg_baselines[video_key], dtype=np.float32)
            fnirs = np.asarray(fnirs_baselines[video_key], dtype=np.float32)
            eeg = eeg - eeg.mean(axis=1, keepdims=True)
            fnirs = fnirs - fnirs.mean(axis=2, keepdims=True)
            n_seconds = _infer_baseline_seconds(eeg)
            eeg_features = _append_second_context(_eeg_features_by_second(eeg, n_seconds))
            fnirs_features = _append_second_context(_fnirs_features_by_second(fnirs, n_seconds))
            n = min(eeg_features.shape[0], fnirs_features.shape[0])
            eeg_parts.append(eeg_features[:n])
            fnirs_parts.append(fnirs_features[:n])
            expanded_keys.extend([(subject, video)] * n)

    if not eeg_parts:
        return [], np.empty((0, 64, 45), dtype=np.float32), np.empty((0, 51, 90), dtype=np.float32)
    return (
        expanded_keys,
        np.concatenate(eeg_parts, axis=0).astype(np.float32),
        np.concatenate(fnirs_parts, axis=0).astype(np.float32),
    )


def average_baseline_predictions(
    keys: Sequence[tuple[str, int]],
    predictions: np.ndarray,
) -> dict[tuple[str, int], np.ndarray]:
    grouped: dict[tuple[str, int], list[np.ndarray]] = {}
    for key, pred in zip(keys, np.asarray(predictions, dtype=np.float32)):
        grouped.setdefault(key, []).append(pred)
    return {
        key: np.mean(np.stack(values, axis=0), axis=0).astype(np.float32)
        for key, values in grouped.items()
    }


def _infer_baseline_seconds(eeg: np.ndarray) -> int:
    if eeg.ndim != 2:
        raise ValueError(f"Expected EEG baseline shape [channels, time], got {eeg.shape}")
    samples = int(eeg.shape[1])
    if samples <= 0:
        return 1
    return max(1, int(round(samples / 1000.0)))
