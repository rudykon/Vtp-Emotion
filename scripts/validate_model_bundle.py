#!/usr/bin/env python3
"""Validate a local MER-PS model bundle on selected training/validation rows."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = PROJECT / "data" / "MER_PS_trainval"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle_path", type=Path)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--subject", default="test_1")
    parser.add_argument("--video", default="1")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Copy the validated predictions.csv file to this path.",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    bundle_path = args.bundle_path.resolve()
    data_root = args.data_root.resolve()
    if not bundle_path.exists():
        raise SystemExit(f"missing model bundle: {bundle_path}")
    if not (data_root / "data").is_dir():
        raise SystemExit(f"missing data directory: {data_root / 'data'}")

    sample_ids = [
        f"{args.subject}_V{int(args.video):02d}_T{idx:03d}"
        for idx in range(args.start, args.start + args.count)
    ]
    with tempfile.TemporaryDirectory(prefix="merps_bundle_validation_") as tmp:
        root = Path(tmp)
        bundle_dir = root / "bundle"
        input_dir = root / "input"
        output_dir = root / "output"
        bundle_dir.mkdir()
        input_dir.mkdir()
        output_dir.mkdir()

        with zipfile.ZipFile(bundle_path) as zf:
            zf.extractall(bundle_dir)
        if not (bundle_dir / "model.py").exists():
            raise SystemExit("model bundle does not contain root model.py")

        (input_dir / "data").symlink_to(data_root / "data", target_is_directory=True)
        write_sample_ids(input_dir / "sample_ids.csv", sample_ids)
        module = load_model_bundle(bundle_dir / "model.py")
        module.predict(str(input_dir), str(output_dir))

        rows = read_predictions(output_dir / "predictions.csv")
        if len(rows) != len(sample_ids):
            raise SystemExit(f"expected {len(sample_ids)} predictions, got {len(rows)}")
        missing = set(sample_ids) - {row["sample_id"] for row in rows}
        if missing:
            raise SystemExit(f"missing predictions for: {sorted(missing)[:3]}")

        if args.output_csv is not None:
            destination = args.output_csv.resolve()
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(output_dir / "predictions.csv", destination)
        print(f"Validation OK: {bundle_path.name} rows={len(rows)} first={rows[0]}")


def write_sample_ids(path: Path, sample_ids: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sample_id"])
        writer.writeheader()
        for sample_id in sample_ids:
            writer.writerow({"sample_id": sample_id})


def load_model_bundle(path: Path):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("model_bundle_entry", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_predictions(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    main()
