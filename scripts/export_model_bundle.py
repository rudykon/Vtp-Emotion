#!/usr/bin/env python3
"""Export the low-MAE MER-PS fixed-fusion inference bundle.

The default bundle uses the paper's fixed video--time prior weights and disables
resting-output calibration. It is a full-data reproducibility artifact; the
paper's MAE estimates are obtained from participant-held-out folds.
"""

from __future__ import annotations

import argparse
import csv
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable

import numpy as np

PROJECT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT / "src" / "merps"
CHECKPOINT_DIR = PROJECT / "checkpoints"
OUTPUT_DIR = PROJECT / "artifacts"
DEFAULT_VARIANT = "source_explicit"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--checkpoint-dir", type=Path, default=CHECKPOINT_DIR)
    parser.add_argument("--variant", default=DEFAULT_VARIANT)
    parser.add_argument("--valence-weight", type=float, default=0.99)
    parser.add_argument("--arousal-weight", type=float, default=0.92)
    parser.add_argument("--bias-mode", choices=("subject", "trial"), default="subject")
    parser.add_argument("--bias-shrink-valence", type=float, default=0.0)
    parser.add_argument("--bias-shrink-arousal", type=float, default=0.0)
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else PROJECT / args.output_dir
    checkpoint_dir = args.checkpoint_dir if args.checkpoint_dir.is_absolute() else PROJECT / args.checkpoint_dir
    prior_weights = np.asarray(
        [args.valence_weight, args.arousal_weight],
        dtype=np.float32,
    )
    bias_shrink = np.asarray(
        [args.bias_shrink_valence, args.bias_shrink_arousal],
        dtype=np.float32,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    prior = ensure_prior(checkpoint_dir)
    full_model, fold_models = resolve_model_paths(checkpoint_dir)
    bundle_path = output_dir / f"model_bundle_{args.variant}.zip"

    with tempfile.TemporaryDirectory(prefix="merps_bundle_") as tmp:
        prior_path = Path(tmp) / "video_time_prior.npz"
        write_prior(
            prior,
            prior_path,
            prior_weights=prior_weights,
            bias_shrink=bias_shrink,
            bias_mode=args.bias_mode,
            variant=args.variant,
        )
        export_bundle(bundle_path, prior_path, full_model, fold_models)

    append_manifest(
        output_dir / "manifest.csv",
        [
            {
                "bundle": bundle_path.name,
                "variant": args.variant,
                "valence_prior_weight": float(prior_weights[0]),
                "arousal_prior_weight": float(prior_weights[1]),
                "resting_bias_mode": args.bias_mode,
                "resting_bias_shrink_valence": float(bias_shrink[0]),
                "resting_bias_shrink_arousal": float(bias_shrink[1]),
                "num_physiology_checkpoints": 1 + len(fold_models),
                "note": "Full-data fixed-fusion bundle for low-MAE inference reproducibility.",
            }
        ],
    )
    print(f"Wrote {display_path(bundle_path)}")
    print(f"Manifest: {display_path(output_dir / 'manifest.csv')}")


def display_path(path: Path) -> Path:
    try:
        return path.relative_to(PROJECT)
    except ValueError:
        return path


def ensure_prior(checkpoint_dir: Path = CHECKPOINT_DIR) -> Path:
    prior_path = checkpoint_dir / "label_prior.npz"
    if not prior_path.exists():
        raise FileNotFoundError(prior_path)
    return prior_path


def resolve_model_paths(checkpoint_dir: Path = CHECKPOINT_DIR) -> tuple[Path, list[Path]]:
    full_model = checkpoint_dir / "final_v3.pt"
    if not full_model.exists():
        full_model = checkpoint_dir / "best_v3.pt"
    if not full_model.exists():
        raise FileNotFoundError("No full-data physiological checkpoint was found.")

    fold_models = [checkpoint_dir / f"fold_{idx}_best.pt" for idx in range(5)]
    missing = [path for path in fold_models if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing participant-fold checkpoints: {missing}")
    return full_model, fold_models


def write_prior(
    base_path: Path,
    output_path: Path,
    *,
    prior_weights: np.ndarray,
    bias_shrink: float | np.ndarray,
    bias_mode: str,
    variant: str = DEFAULT_VARIANT,
) -> None:
    with np.load(base_path, allow_pickle=False) as data:
        prior = {key: data[key] for key in data.files}
    prior["blend_weights"] = np.asarray(prior_weights, dtype=np.float32)
    prior["baseline_bias_shrink"] = np.asarray(bias_shrink, dtype=np.float32)
    prior["baseline_bias_mode"] = np.asarray(bias_mode)
    prior["analysis_variant"] = np.asarray(variant)
    np.savez_compressed(output_path, **prior)


def export_bundle(
    bundle_path: Path,
    prior_path: Path,
    full_model: Path,
    fold_models: list[Path],
) -> None:
    with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(SOURCE_DIR / "inference.py", "model.py")
        for py_file in ("calibration.py", "features.py", "prior.py", "model.py"):
            zf.write(SOURCE_DIR / py_file, f"merps/{py_file}")
        zf.writestr("merps/__init__.py", "")
        zf.write(full_model, "physiology_full.pt")
        for idx, path in enumerate(fold_models):
            zf.write(path, f"physiology_fold_{idx}.pt")
        zf.write(prior_path, "video_time_prior.npz")


def append_manifest(path: Path, rows: Iterable[dict[str, object]]) -> None:
    rows = list(rows)
    existing: list[dict[str, str]] = []
    if path.exists():
        with path.open("r", newline="", encoding="utf-8") as handle:
            existing = list(csv.DictReader(handle))

    replacements = {str(row["bundle"]) for row in rows}
    all_rows = [row for row in existing if row.get("bundle") not in replacements] + rows
    fieldnames: list[str] = []
    for row in all_rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(all_rows)


if __name__ == "__main__":
    main()
