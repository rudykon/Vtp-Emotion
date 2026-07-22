"""Inference entry point for the source-explicit MER-PS model bundle.

The bundle combines a full-data video--time prior with an EEG--fNIRS
physiological ensemble. Its default metadata matches the paper's descriptive
fusion weights and disables resting-output calibration.
"""

import csv
import sys
from pathlib import Path

import numpy as np
import torch

BUNDLE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BUNDLE_DIR))

from merps.calibration import (
    aggregate_baseline_bias,
    apply_baseline_bias_correction,
    average_baseline_predictions,
    build_baseline_prediction_features,
)
from merps.features import apply_standardization, build_prediction_features, read_sample_rows
from merps.model import MERPSNetV3
from merps.prior import load_label_prior, predict_label_prior

PRIOR_PATH = BUNDLE_DIR / "video_time_prior.npz"
BATCH_SIZE = 256


def predict(input_dir: str, output_dir: str) -> None:
    """Predict valence and arousal for the sample keys under ``input_dir``."""

    torch.set_num_threads(min(4, max(1, torch.get_num_threads())))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    rows = read_sample_rows(input_dir)
    sample_ids = [str(row["sample_id"]) for row in rows]

    prior = None
    prior_prediction = None
    if PRIOR_PATH.exists():
        prior = load_label_prior(PRIOR_PATH)
        prior_prediction = predict_label_prior(rows, prior)

    physiology_prediction = None
    checkpoint_paths = _checkpoint_paths()
    if checkpoint_paths:
        try:
            physiology_prediction = _predict_with_source_explicit_ensemble(
                input_dir,
                rows,
                device,
                checkpoint_paths,
                prior,
            )
        except Exception:
            if prior_prediction is None:
                raise

    if prior_prediction is not None and physiology_prediction is not None:
        weights = np.asarray(prior.get("blend_weights", [0.99, 0.92]), dtype=np.float32)
        preds = weights[None, :] * prior_prediction + (1.0 - weights[None, :]) * physiology_prediction
    elif prior_prediction is not None:
        preds = prior_prediction
    elif physiology_prediction is not None:
        preds = physiology_prediction
    else:
        raise FileNotFoundError(
            "Missing both video_time_prior.npz and physiological checkpoints"
        )

    preds = np.rint(np.asarray(preds)).astype(np.int16)
    preds = np.clip(preds, 1, 255)

    output_path = Path(output_dir) / "predictions.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sample_id", "valence", "arousal"])
        writer.writeheader()
        for sample_id, values in zip(sample_ids, preds):
            writer.writerow(
                {
                    "sample_id": sample_id,
                    "valence": int(values[0]),
                    "arousal": int(values[1]),
                }
            )


def _checkpoint_paths() -> list[Path]:
    paths: list[Path] = []
    full_path = BUNDLE_DIR / "physiology_full.pt"
    if full_path.exists():
        paths.append(full_path)
    paths.extend(sorted(BUNDLE_DIR.glob("physiology_fold_*.pt")))
    return paths


def _predict_with_source_explicit_ensemble(
    input_dir: str,
    rows: list[dict[str, object]],
    device: torch.device,
    checkpoint_paths: list[Path],
    prior: dict[str, np.ndarray] | None,
) -> np.ndarray:
    sample_ids, eeg, fnirs = build_prediction_features(input_dir, rows)
    if len(sample_ids) != len(rows):
        raise ValueError("Feature construction returned a different number of samples")

    baseline_keys, baseline_eeg, baseline_fnirs = build_baseline_prediction_features(
        input_dir,
        rows,
    )
    predictions = []
    baseline_by_checkpoint = []
    for path in checkpoint_paths:
        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
        eeg_n, fnirs_n = apply_standardization(
            eeg,
            fnirs,
            checkpoint["standardization"],
        )
        model = MERPSNetV3(**checkpoint["model_config"]).to(device)
        model.load_state_dict(checkpoint["model_state"])
        model.eval()
        predictions.append(_predict_batches(model, eeg_n, fnirs_n, device))

        if len(baseline_keys):
            baseline_eeg_n, baseline_fnirs_n = apply_standardization(
                baseline_eeg,
                baseline_fnirs,
                checkpoint["standardization"],
            )
            baseline_by_checkpoint.append(
                average_baseline_predictions(
                    baseline_keys,
                    _predict_batches(model, baseline_eeg_n, baseline_fnirs_n, device),
                )
            )

    physiology_prediction = np.mean(np.stack(predictions, axis=0), axis=0).astype(np.float32)
    if baseline_by_checkpoint:
        baseline_prediction = _mean_prediction_dicts(baseline_by_checkpoint)
        mode = (
            str(np.asarray(prior.get("baseline_bias_mode", "subject")).item())
            if prior is not None
            else "subject"
        )
        shrink = (
            np.asarray(prior.get("baseline_bias_shrink", [0.0, 0.0]), dtype=np.float32)
            if prior is not None
            else np.asarray([0.0, 0.0], dtype=np.float32)
        )
        bias = aggregate_baseline_bias(rows, baseline_prediction, mode=mode)
        physiology_prediction = apply_baseline_bias_correction(
            rows,
            physiology_prediction,
            bias,
            shrink=shrink,
        )
    return physiology_prediction.astype(np.float32)


def _predict_batches(
    model: MERPSNetV3,
    eeg: np.ndarray,
    fnirs: np.ndarray,
    device: torch.device,
) -> np.ndarray:
    outputs = []
    with torch.no_grad():
        for start in range(0, eeg.shape[0], BATCH_SIZE):
            end = min(start + BATCH_SIZE, eeg.shape[0])
            eeg_batch = torch.from_numpy(np.ascontiguousarray(eeg[start:end])).float().to(device)
            fnirs_batch = torch.from_numpy(np.ascontiguousarray(fnirs[start:end])).float().to(device)
            prediction, _ = model(eeg_batch, fnirs_batch)
            outputs.append(
                np.clip(prediction.cpu().numpy() * 254.0 + 1.0, 1.0, 255.0)
            )
    return np.concatenate(outputs, axis=0).astype(np.float32)


def _mean_prediction_dicts(
    items: list[dict[tuple[str, int], np.ndarray]],
) -> dict[tuple[str, int], np.ndarray]:
    keys = sorted(set().union(*(set(item) for item in items)))
    output = {}
    for key in keys:
        values = [item[key] for item in items if key in item]
        output[key] = np.mean(np.stack(values, axis=0), axis=0).astype(np.float32)
    return output
