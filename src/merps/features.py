from __future__ import annotations

import csv
import re
import struct
import zlib
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_ROOT = PROJECT_ROOT / "data" / "MER_PS_trainval"

EEG_TARGET_RATE = 200
EEG_BANDS: tuple[tuple[str, float, float], ...] = (
    ("delta", 1.0, 4.0),
    ("theta", 4.0, 8.0),
    ("alpha", 8.0, 13.0),
    ("beta_low", 13.0, 20.0),
    ("beta_high", 20.0, 30.0),
    ("gamma", 30.0, 45.0),
)
FNIRS_TYPES = tuple(range(6))
FNIRS_STATS = ("mean", "std", "slope", "skewness", "kurtosis")
CONTEXT_RADIUS_SECONDS = 1
EPS = 1e-12

SAMPLE_RE = re.compile(r"^(?P<subject>.+)_V(?P<video>\d+)_T(?P<timestamp>\d+)$")
VIDEO_RE = re.compile(r"^video_(\d+)$")
SUBJECT_RE = re.compile(r"^test_(\d+)$")

MI_INT8 = 1
MI_UINT8 = 2
MI_INT16 = 3
MI_UINT16 = 4
MI_INT32 = 5
MI_UINT32 = 6
MI_SINGLE = 7
MI_DOUBLE = 9
MI_INT64 = 12
MI_UINT64 = 13
MI_MATRIX = 14
MI_COMPRESSED = 15
MI_TO_DTYPE = {
    MI_INT8: np.dtype("i1"),
    MI_UINT8: np.dtype("u1"),
    MI_INT16: np.dtype("<i2"),
    MI_UINT16: np.dtype("<u2"),
    MI_INT32: np.dtype("<i4"),
    MI_UINT32: np.dtype("<u4"),
    MI_SINGLE: np.dtype("<f4"),
    MI_DOUBLE: np.dtype("<f8"),
    MI_INT64: np.dtype("<i8"),
    MI_UINT64: np.dtype("<u8"),
}


def read_sample_rows(input_dir: str | Path) -> list[dict[str, object]]:
    sample_path = Path(input_dir) / "sample_ids.csv"
    if not sample_path.exists():
        raise FileNotFoundError(f"Missing sample_ids.csv in {input_dir}")

    rows: list[dict[str, object]] = []
    with sample_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if "sample_id" not in (reader.fieldnames or []):
            raise ValueError("sample_ids.csv must contain a sample_id column")
        for row in reader:
            sample_id = row["sample_id"].strip()
            match = SAMPLE_RE.match(sample_id)
            if not match:
                raise ValueError(f"Invalid sample_id format: {sample_id}")
            rows.append(
                {
                    "sample_id": sample_id,
                    "subject": match.group("subject"),
                    "video": int(match.group("video")),
                    "timestamp": int(match.group("timestamp")),
                }
            )
    if not rows:
        raise ValueError("sample_ids.csv has no rows")
    return rows


def load_enhanced_features(
    data_root: str | Path,
    subjects: Iterable[str] | None = None,
    baseline_correction: bool = True,
    fnirs_hrf_shift_seconds: int = 0,
    verbose: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str]]:
    data_root = Path(data_root)
    subject_names = list(subjects) if subjects is not None else discover_subjects(data_root)
    if not subject_names:
        raise ValueError(f"No subject folders found under {data_root / 'data'}")

    eeg_samples: list[np.ndarray] = []
    fnirs_samples: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    sample_subjects: list[str] = []

    for subject_index, subject in enumerate(subject_names, start=1):
        if verbose:
            print(f"[features] loading subject {subject_index}/{len(subject_names)}: {subject}", flush=True)
        subject_dir = data_root / "data" / subject
        labels = _load_mat(data_root / "annotations" / f"{subject}_label.mat")
        mats = _load_subject_mats(subject_dir, baseline_correction=baseline_correction)
        video_keys = _video_keys(labels)

        for video_index, video_key in enumerate(video_keys, start=1):
            label = _label_matrix(labels[video_key])
            n_labels = int(label.shape[1])
            eeg_by_second, fnirs_by_second = _features_for_trial_from_mats(
                mats,
                video_key,
                n_labels,
                baseline_correction=baseline_correction,
                fnirs_hrf_shift_seconds=fnirs_hrf_shift_seconds,
            )
            y_by_second = np.clip((label - 1.0) / 254.0, 0.0, 1.0).T.astype(np.float32)
            n = min(eeg_by_second.shape[0], fnirs_by_second.shape[0], y_by_second.shape[0])
            eeg_samples.append(eeg_by_second[:n])
            fnirs_samples.append(fnirs_by_second[:n])
            targets.append(y_by_second[:n])
            sample_subjects.extend([subject] * n)

            if verbose and (video_index == len(video_keys) or video_index % 5 == 0):
                print(
                    f"[features] {subject}: processed {video_index}/{len(video_keys)} videos",
                    flush=True,
                )

    return (
        np.concatenate(eeg_samples, axis=0).astype(np.float32),
        np.concatenate(fnirs_samples, axis=0).astype(np.float32),
        np.concatenate(targets, axis=0).astype(np.float32),
        np.asarray(sample_subjects),
        subject_names,
    )


def build_prediction_features(
    input_dir: str | Path,
    rows: Sequence[dict[str, object]],
    baseline_correction: bool = True,
    fnirs_hrf_shift_seconds: int = 0,
) -> tuple[list[str], np.ndarray, np.ndarray]:
    input_dir = Path(input_dir)
    grouped: dict[tuple[str, int], list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault((str(row["subject"]), int(row["video"])), []).append(row)

    feature_cache: dict[tuple[str, int], tuple[np.ndarray, np.ndarray]] = {}
    for subject in sorted({subject for subject, _ in grouped}):
        subject_dir = input_dir / "data" / subject
        mats = _load_subject_mats(subject_dir, baseline_correction=baseline_correction)
        for _, video in sorted(key for key in grouped if key[0] == subject):
            key = (subject, video)
            max_timestamp = max(int(item["timestamp"]) for item in grouped[key])
            n_labels = max_timestamp + 1
            feature_cache[key] = _features_for_trial_from_mats(
                mats,
                f"video_{video}",
                n_labels,
                baseline_correction=baseline_correction,
                fnirs_hrf_shift_seconds=fnirs_hrf_shift_seconds,
            )

    sample_ids: list[str] = []
    eeg_samples: list[np.ndarray] = []
    fnirs_samples: list[np.ndarray] = []
    for row in rows:
        subject = str(row["subject"])
        video = int(row["video"])
        timestamp = int(row["timestamp"])
        eeg_by_second, fnirs_by_second = feature_cache[(subject, video)]
        if timestamp >= eeg_by_second.shape[0]:
            raise ValueError(f"{row['sample_id']} timestamp exceeds available signal length")
        sample_ids.append(str(row["sample_id"]))
        eeg_samples.append(eeg_by_second[timestamp])
        fnirs_samples.append(fnirs_by_second[timestamp])

    return (
        sample_ids,
        np.stack(eeg_samples, axis=0).astype(np.float32),
        np.stack(fnirs_samples, axis=0).astype(np.float32),
    )


def standardize_features(
    eeg: np.ndarray,
    fnirs: np.ndarray,
    train_idx: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    train_idx = np.asarray(train_idx, dtype=np.int64)
    if train_idx.size == 0:
        raise ValueError("train_idx must contain at least one sample")

    eeg_mean = eeg[train_idx].mean(axis=(0, 1), keepdims=True)
    eeg_std = np.maximum(eeg[train_idx].std(axis=(0, 1), keepdims=True), 1e-6)
    fnirs_mean = fnirs[train_idx].mean(axis=(0, 1), keepdims=True)
    fnirs_std = np.maximum(fnirs[train_idx].std(axis=(0, 1), keepdims=True), 1e-6)
    stats = {
        "eeg_mean": eeg_mean.astype(np.float32),
        "eeg_std": eeg_std.astype(np.float32),
        "fnirs_mean": fnirs_mean.astype(np.float32),
        "fnirs_std": fnirs_std.astype(np.float32),
    }
    return apply_standardization(eeg, fnirs, stats) + (stats,)


def apply_standardization(
    eeg: np.ndarray,
    fnirs: np.ndarray,
    stats: dict[str, np.ndarray],
) -> tuple[np.ndarray, np.ndarray]:
    eeg_mean = np.asarray(stats["eeg_mean"], dtype=np.float32)
    eeg_std = np.maximum(np.asarray(stats["eeg_std"], dtype=np.float32), 1e-6)
    fnirs_mean = np.asarray(stats["fnirs_mean"], dtype=np.float32)
    fnirs_std = np.maximum(np.asarray(stats["fnirs_std"], dtype=np.float32), 1e-6)
    return (
        ((eeg - eeg_mean) / eeg_std).astype(np.float32),
        ((fnirs - fnirs_mean) / fnirs_std).astype(np.float32),
    )


def discover_subjects(data_root: str | Path) -> list[str]:
    data_dir = Path(data_root) / "data"
    subjects = [
        path.name
        for path in data_dir.iterdir()
        if path.is_dir() and SUBJECT_RE.fullmatch(path.name)
    ]
    return sorted(subjects, key=lambda item: int(item.split("_", 1)[1]))


def _features_for_trial_from_mats(
    mats: dict[str, dict[str, np.ndarray]],
    video_key: str,
    n_labels: int,
    baseline_correction: bool,
    fnirs_hrf_shift_seconds: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    eeg_videos = mats["eeg_videos"]
    fnirs_videos = mats["fnirs_videos"]
    if video_key not in eeg_videos or video_key not in fnirs_videos:
        raise ValueError(f"Missing {video_key} in subject matrices")

    eeg = np.asarray(eeg_videos[video_key], dtype=np.float32)
    fnirs = np.asarray(fnirs_videos[video_key], dtype=np.float32)
    if baseline_correction:
        eeg = _subtract_eeg_baseline(eeg, mats["eeg_baselines"].get(video_key))
        fnirs = _subtract_fnirs_baseline(fnirs, mats["fnirs_baselines"].get(video_key))

    eeg_features = _append_second_context(_eeg_features_by_second(eeg, n_labels))
    fnirs_features = _append_second_context(
        _fnirs_features_by_second(
            fnirs,
            n_labels,
            hrf_shift_seconds=fnirs_hrf_shift_seconds,
        )
    )
    return eeg_features, fnirs_features


def _load_subject_mats(subject_dir: Path, baseline_correction: bool) -> dict[str, dict[str, np.ndarray]]:
    mats = {
        "eeg_videos": _load_mat(subject_dir / "EEG_videos.mat"),
        "fnirs_videos": _load_mat(subject_dir / "fNIRS_videos.mat"),
    }
    if baseline_correction:
        mats["eeg_baselines"] = _load_mat(subject_dir / "EEG_baselines.mat")
        mats["fnirs_baselines"] = _load_mat(subject_dir / "fNIRS_baselines.mat")
    return mats


def _load_mat(path: Path) -> dict[str, np.ndarray]:
    if not path.exists():
        raise FileNotFoundError(path)
    return read_mat_v5(path)


def read_mat_v5(path: Path) -> dict[str, np.ndarray]:
    with path.open("rb") as handle:
        header = handle.read(128)
        if len(header) != 128 or b"MATLAB 5.0 MAT-file" not in header[:116]:
            raise ValueError(f"Unsupported .mat file format: {path}")
        payload = handle.read()

    arrays: dict[str, np.ndarray] = {}
    for data_type, data in _iter_elements(payload):
        if data_type == MI_COMPRESSED:
            for inner_type, inner_data in _iter_elements(zlib.decompress(data)):
                if inner_type == MI_MATRIX:
                    name, array = _parse_matrix(inner_data)
                    arrays[name] = array
        elif data_type == MI_MATRIX:
            name, array = _parse_matrix(data)
            arrays[name] = array
    return arrays


def _iter_elements(buffer: bytes):
    offset = 0
    size = len(buffer)
    while offset + 8 <= size:
        data_type, data, offset = _read_element(buffer, offset)
        if data_type == 0 and len(data) == 0:
            break
        yield data_type, data


def _read_element(buffer: bytes, offset: int) -> tuple[int, bytes, int]:
    raw = struct.unpack_from("<I", buffer, offset)[0]
    small_nbytes = raw >> 16
    if small_nbytes:
        data_type = raw & 0xFFFF
        data_start = offset + 4
        data_end = data_start + small_nbytes
        return data_type, buffer[data_start:data_end], offset + 8

    data_type, nbytes = struct.unpack_from("<II", buffer, offset)
    data_start = offset + 8
    data_end = data_start + nbytes
    next_offset = data_end + ((8 - (nbytes % 8)) % 8)
    return data_type, buffer[data_start:data_end], next_offset


def _parse_matrix(data: bytes) -> tuple[str, np.ndarray]:
    offset = 0
    _, _, offset = _read_element(data, offset)

    dim_type, dim_data, offset = _read_element(data, offset)
    if dim_type not in (MI_INT32, MI_UINT32):
        raise ValueError("Unsupported MATLAB dimension element")
    dims = np.frombuffer(dim_data, dtype=MI_TO_DTYPE[dim_type]).astype(np.int64)

    name_type, name_data, offset = _read_element(data, offset)
    if name_type not in (MI_INT8, MI_UINT8):
        raise ValueError("Unsupported MATLAB variable name element")
    name = bytes(name_data).decode("utf-8").rstrip("\x00")

    real_type, real_data, _ = _read_element(data, offset)
    if real_type not in MI_TO_DTYPE:
        raise ValueError(f"Unsupported MATLAB numeric type: {real_type}")
    dtype = MI_TO_DTYPE[real_type]
    array = np.frombuffer(real_data, dtype=dtype)
    if dims.size:
        array = array.reshape(tuple(int(dim) for dim in dims), order="F")
    return name, array


def _video_keys(mat: dict[str, np.ndarray]) -> list[str]:
    keys = [key for key in mat if VIDEO_RE.fullmatch(key)]
    return sorted(keys, key=lambda item: int(item.split("_", 1)[1]))


def _label_matrix(value: np.ndarray) -> np.ndarray:
    label = np.asarray(value, dtype=np.float32)
    if label.ndim != 2:
        raise ValueError(f"Expected label matrix with 2 dims, got shape {label.shape}")
    if label.shape[0] != 2 and label.shape[1] == 2:
        label = label.T
    if label.shape[0] != 2:
        raise ValueError(f"Expected label shape [2, time], got {label.shape}")
    return label


def _subtract_eeg_baseline(eeg: np.ndarray, baseline: np.ndarray | None) -> np.ndarray:
    if baseline is None:
        return eeg
    base = np.asarray(baseline, dtype=np.float32)
    if base.ndim == 2 and base.shape[0] == eeg.shape[0]:
        return eeg - base.mean(axis=1, keepdims=True)
    return eeg


def _subtract_fnirs_baseline(fnirs: np.ndarray, baseline: np.ndarray | None) -> np.ndarray:
    if baseline is None:
        return fnirs
    base = np.asarray(baseline, dtype=np.float32)
    if base.ndim == 3 and base.shape[:2] == fnirs.shape[:2]:
        return fnirs - base.mean(axis=2, keepdims=True)
    return fnirs


def _eeg_features_by_second(eeg: np.ndarray, n_seconds: int) -> np.ndarray:
    channels, n_samples = eeg.shape
    samples_per_second = n_samples / float(n_seconds)
    rounded = int(round(samples_per_second))

    if rounded >= 2 and abs(samples_per_second - rounded) < 1e-4:
        trimmed = eeg[:, : rounded * n_seconds]
        segments = trimmed.reshape(channels, n_seconds, rounded).transpose(1, 0, 2)
    else:
        segments = []
        for idx in range(n_seconds):
            start = int(round(idx * n_samples / n_seconds))
            end = max(int(round((idx + 1) * n_samples / n_seconds)), start + 1)
            segments.append(eeg[:, start:end])
        return np.stack(
            [_eeg_segment_features(_resample_eeg_segment(segment))[0] for segment in segments],
            axis=0,
        ).astype(np.float32)

    segments = _resample_eeg_segments(segments, source_rate=float(rounded))
    return _eeg_segment_features(segments).astype(np.float32)


def _resample_eeg_segments(segments: np.ndarray, source_rate: float) -> np.ndarray:
    length = segments.shape[-1]
    if length == EEG_TARGET_RATE:
        return np.asarray(segments, dtype=np.float32)

    ratio = length / float(EEG_TARGET_RATE)
    if abs(ratio - round(ratio)) < 1e-6 and int(round(ratio)) > 1:
        factor = int(round(ratio))
        usable = EEG_TARGET_RATE * factor
        return segments[..., :usable].reshape(*segments.shape[:-1], EEG_TARGET_RATE, factor).mean(axis=-1).astype(np.float32)

    old_x = np.linspace(0.0, 1.0, num=length, endpoint=False)
    new_x = np.linspace(0.0, 1.0, num=EEG_TARGET_RATE, endpoint=False)
    flat = segments.reshape(-1, length)
    out = np.empty((flat.shape[0], EEG_TARGET_RATE), dtype=np.float32)
    for idx, row in enumerate(flat):
        out[idx] = np.interp(new_x, old_x, row).astype(np.float32)
    return out.reshape(*segments.shape[:-1], EEG_TARGET_RATE)


def _resample_eeg_segment(segment: np.ndarray) -> np.ndarray:
    return _resample_eeg_segments(segment[None, :, :], source_rate=float(segment.shape[-1]))[0]


def _eeg_segment_features(segments: np.ndarray) -> np.ndarray:
    segments = np.asarray(segments, dtype=np.float32)
    if segments.ndim == 2:
        segments = segments[None, :, :]
    centered = segments - segments.mean(axis=-1, keepdims=True)
    length = centered.shape[-1]
    if length < 3:
        return np.zeros((*centered.shape[:2], len(EEG_BANDS) * 2 + 3), dtype=np.float32)

    bandpower, de = _eeg_frequency_features(centered, sampling_rate=float(EEG_TARGET_RATE))
    hjorth = _hjorth_parameters(centered)
    return np.concatenate([bandpower, de, hjorth], axis=-1).astype(np.float32)


def _eeg_frequency_features(
    centered: np.ndarray,
    sampling_rate: float,
) -> tuple[np.ndarray, np.ndarray]:
    length = centered.shape[-1]
    window = np.hanning(length).astype(np.float32)
    windowed_spectrum = np.abs(np.fft.rfft(centered * window, axis=-1)) ** 2
    raw_spectrum = np.fft.rfft(centered, axis=-1)
    freqs = np.fft.rfftfreq(length, d=1.0 / sampling_rate)

    valid = (freqs >= EEG_BANDS[0][1]) & (freqs < EEG_BANDS[-1][2])
    total_power = windowed_spectrum[..., valid].sum(axis=-1) + EPS

    bandpower_parts = []
    de_parts = []
    for _, low, high in EEG_BANDS:
        mask = (freqs >= low) & (freqs < high)
        if not np.any(mask):
            power = np.zeros_like(total_power)
            variance = np.full_like(total_power, EPS)
        else:
            power = windowed_spectrum[..., mask].sum(axis=-1)
            band_fft = np.zeros_like(raw_spectrum)
            band_fft[..., mask] = raw_spectrum[..., mask]
            band_signal = np.fft.irfft(band_fft, n=length, axis=-1)
            variance = np.var(band_signal, axis=-1)
        bandpower_parts.append(np.log(np.maximum(power / total_power, EPS)))
        de_parts.append(0.5 * np.log(2.0 * np.pi * np.e * np.maximum(variance, EPS)))

    return (
        np.stack(bandpower_parts, axis=-1).astype(np.float32),
        np.stack(de_parts, axis=-1).astype(np.float32),
    )


def _hjorth_parameters(segments: np.ndarray) -> np.ndarray:
    activity = np.var(segments, axis=-1)
    diff1 = np.diff(segments, axis=-1)
    diff2 = np.diff(diff1, axis=-1)
    var_diff1 = np.var(diff1, axis=-1)
    var_diff2 = np.var(diff2, axis=-1)
    mobility = np.sqrt(var_diff1 / np.maximum(activity, EPS))
    mobility_diff = np.sqrt(var_diff2 / np.maximum(var_diff1, EPS))
    complexity = mobility_diff / np.maximum(mobility, EPS)
    return np.stack([activity, mobility, complexity], axis=-1).astype(np.float32)


def _fnirs_features_by_second(
    fnirs: np.ndarray,
    n_seconds: int,
    hrf_shift_seconds: int = 0,
) -> np.ndarray:
    fnirs = np.asarray(fnirs, dtype=np.float32)
    selected = fnirs[np.asarray(FNIRS_TYPES, dtype=np.int64)]
    _, channels, n_samples = selected.shape
    feature_dim = len(FNIRS_TYPES) * len(FNIRS_STATS)
    features = np.empty((n_seconds, channels, feature_dim), dtype=np.float32)
    shift = int(hrf_shift_seconds)

    for idx in range(n_seconds):
        source_idx = min(max(idx + shift, 0), n_seconds - 1)
        start = int(round(source_idx * n_samples / n_seconds))
        end = max(int(round((source_idx + 1) * n_samples / n_seconds)), start + 1)
        segment = selected[:, :, start:end]
        features[idx] = _fnirs_segment_features(segment)
    return features


def _fnirs_segment_features(segment: np.ndarray) -> np.ndarray:
    types, channels, length = segment.shape
    mean = segment.mean(axis=-1)
    centered = segment - mean[..., None]
    std = segment.std(axis=-1)
    safe_std = np.maximum(std, 1e-6)

    if length >= 2:
        t = np.arange(length, dtype=np.float32)
        t -= t.mean()
        slope = (centered * t).sum(axis=-1) / np.maximum(float((t * t).sum()), EPS)
    else:
        slope = np.zeros((types, channels), dtype=np.float32)

    z = centered / safe_std[..., None]
    skewness = np.mean(z**3, axis=-1)
    kurtosis = np.mean(z**4, axis=-1) - 3.0
    constant = std < 1e-6
    skewness = np.where(constant, 0.0, skewness)
    kurtosis = np.where(constant, 0.0, kurtosis)

    parts = [mean, std, slope, skewness, kurtosis]
    return np.concatenate([part.T for part in parts], axis=1).astype(np.float32)


def _append_second_context(features: np.ndarray, radius: int = CONTEXT_RADIUS_SECONDS) -> np.ndarray:
    if radius <= 0:
        return np.asarray(features, dtype=np.float32)
    if features.ndim != 3:
        raise ValueError(f"Expected [seconds, channels, features], got {features.shape}")

    padded = np.pad(features, ((radius, radius), (0, 0), (0, 0)), mode="edge")
    n = features.shape[0]
    windows = [padded[offset : offset + n] for offset in range(2 * radius + 1)]
    return np.concatenate(windows, axis=-1).astype(np.float32)


load_training_features = load_enhanced_features
standardize_from_train = standardize_features


def main() -> None:
    eeg, fnirs, y, subjects, subject_names = load_enhanced_features(DEFAULT_DATA_ROOT, verbose=True)
    print("[features] loaded")
    print(f"  subjects: {len(subject_names)} ({', '.join(subject_names[:3])} ... {subject_names[-1]})")
    print(f"  eeg: {eeg.shape}  flattened_dim={eeg.shape[1] * eeg.shape[2]}")
    print(f"  fnirs: {fnirs.shape}  flattened_dim={fnirs.shape[1] * fnirs.shape[2]}")
    print(f"  y: {y.shape}")
    print(f"  sample_subjects: {subjects.shape}")


if __name__ == "__main__":
    main()
