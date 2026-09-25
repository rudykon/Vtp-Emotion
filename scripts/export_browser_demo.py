#!/usr/bin/env python3
"""Export private, local-only model and feature files for the browser demo.

Outputs belong in artifacts/ and must not be published with the static site.
The browser consumes prepared features; MAT preprocessing remains a local step.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
from pathlib import Path
import sys

import numpy as np
import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
from merps.features import build_prediction_features
from merps.model import MERPSNetV3
from merps.prior import load_label_prior
from scripts.export_model_bundle import resolve_model_paths

FEATURE_VERSION = "merps-context-r1-baseline-v1"
MAX_SAMPLES = 300


class BrowserPhysiology(nn.Module):
    """Standardize with each checkpoint, predict, scale, then average in float32."""

    def __init__(self, checkpoints):
        super().__init__()
        self.models = nn.ModuleList()
        for index, checkpoint in enumerate(checkpoints):
            config = checkpoint["model_config"]
            expected = {"eeg_nodes": 64, "eeg_features": 45, "fnirs_nodes": 51,
                        "fnirs_features": 90, "output_dim": 2}
            if any(config.get(key, value) != value for key, value in expected.items()):
                raise ValueError("Checkpoint dimensions do not match the browser feature contract")
            model = MERPSNetV3(**config)
            model.load_state_dict(checkpoint["model_state"])
            self.models.append(model.eval())
            for name in ("eeg_mean", "eeg_std", "fnirs_mean", "fnirs_std"):
                values = np.asarray(checkpoint["standardization"][name], dtype=np.float32)
                expected = 45 if name.startswith("eeg") else 90
                if values.shape != (1, 1, expected) or not np.isfinite(values).all():
                    raise ValueError(f"Invalid standardization: {name} {values.shape}")
                if name.endswith("_std"):
                    values = np.maximum(values, 1e-6)
                self.register_buffer(f"{name}_{index}", torch.from_numpy(values))

    def forward(self, eeg, fnirs):
        outputs = []
        for index, model in enumerate(self.models):
            eeg_n = (eeg - getattr(self, f"eeg_mean_{index}")) / getattr(self, f"eeg_std_{index}")
            fnirs_n = (fnirs - getattr(self, f"fnirs_mean_{index}")) / getattr(self, f"fnirs_std_{index}")
            prediction, _ = model(eeg_n, fnirs_n)
            outputs.append(torch.clamp(prediction * 254.0 + 1.0, 1.0, 255.0))
        return torch.stack(outputs).mean(dim=0)


def write_private_json(path, payload, force=False):
    path = Path(path)
    if path.exists() and not force:
        raise FileExistsError(f"Already exists: {path}. Choose another output or use --force.")
    content = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"Saved local-only file: {path} ({len(content.encode('utf-8')):,} bytes)")


def export_model(checkpoint_dir, output, force=False):
    import onnx
    import onnxruntime as ort

    full, folds = resolve_model_paths(Path(checkpoint_dir))
    paths = [full, *folds]
    checkpoints = [torch.load(path, map_location="cpu", weights_only=True) for path in paths]
    model = BrowserPhysiology(checkpoints).eval()
    rng = np.random.default_rng(2026)
    eeg = rng.normal(size=(3, 64, 45)).astype(np.float32)
    fnirs = rng.normal(size=(3, 51, 90)).astype(np.float32)
    eeg = eeg * np.asarray(checkpoints[0]["standardization"]["eeg_std"], dtype=np.float32) + np.asarray(checkpoints[0]["standardization"]["eeg_mean"], dtype=np.float32)
    fnirs = fnirs * np.asarray(checkpoints[0]["standardization"]["fnirs_std"], dtype=np.float32) + np.asarray(checkpoints[0]["standardization"]["fnirs_mean"], dtype=np.float32)
    buffer = io.BytesIO()
    torch.onnx.export(
        model, (torch.from_numpy(eeg[:2]), torch.from_numpy(fnirs[:2])), buffer,
        input_names=["eeg", "fnirs"], output_names=["physiology"],
        dynamic_axes={"eeg": {0: "samples"}, "fnirs": {0: "samples"}, "physiology": {0: "samples"}},
        opset_version=17, do_constant_folding=True,
    )
    model_bytes = buffer.getvalue()
    onnx.checker.check_model(onnx.load_model_from_string(model_bytes))
    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(model_bytes, sess_options=options, providers=["CPUExecutionProvider"])
    errors = []
    for count in (1, 3):
        with torch.inference_mode():
            expected = model(torch.from_numpy(eeg[:count]), torch.from_numpy(fnirs[:count])).numpy()
        actual = session.run(["physiology"], {"eeg": eeg[:count], "fnirs": fnirs[:count]})[0]
        np.testing.assert_allclose(actual, expected, rtol=1e-5, atol=1e-3)
        errors.append(float(np.max(np.abs(actual - expected))))
    prior = load_label_prior(Path(checkpoint_dir) / "label_prior.npz")
    trajectories = {}
    for video, length in enumerate(prior["video_lengths"]):
        if int(length) > 0:
            values = np.asarray(prior["values"][video, :int(length)], dtype=np.float32)
            if values.shape[1:] != (2,) or not np.isfinite(values).all():
                raise ValueError(f"Invalid video-time prior for video {video}")
            trajectories[str(video)] = values.tolist()
    payload = {
        "format": "vtp-browser-model-v1", "feature_version": FEATURE_VERSION,
        "input_shapes": {"eeg": [64, 45], "fnirs": [51, 90]}, "label_scale": [1, 255],
        "model_count": len(paths), "checkpoints": [p.name for p in paths],
        "full_checkpoint": full.name, "resting_bias_shrink": [0, 0],
        "default_weights": [0.99, 0.92], "prior": trajectories,
        "physiology_onnx_base64": base64.b64encode(model_bytes).decode("ascii"),
    }
    write_private_json(output, payload, force)
    print(f"ONNX / PyTorch maximum difference: {max(errors):.8f}; {len(paths)} models.")
    if full.name != "final_v3.pt":
        print("Uses best_v3.pt fallback; this is not the ensemble behind the reported 27.72 MAE.")
    return payload


def export_input(data_root, subject, video, start, count, output, force=False):
    if not 1 <= count <= MAX_SAMPLES or start < 0 or not 1 <= video <= 15:
        raise ValueError("Require 1–300 samples, a non-negative start, and video 1–15.")
    if not subject or Path(subject).name != subject or subject in (".", ".."):
        raise ValueError("Subject must be a single folder name")
    rows = [{"sample_id": f"{subject}_V{video:02d}_T{t:03d}", "subject": subject,
             "video": video, "timestamp": t} for t in range(start, start + count)]
    ids, eeg, fnirs = build_prediction_features(data_root, rows)
    if eeg.shape != (count, 64, 45) or fnirs.shape != (count, 51, 90):
        raise ValueError("Unexpected feature dimensions")
    if not np.isfinite(eeg).all() or not np.isfinite(fnirs).all():
        raise ValueError("Features must contain only finite numbers")
    payload = {"format": "vtp-browser-input-v1", "feature_version": FEATURE_VERSION,
               "sample_ids": ids, "video": video, "timestamps": list(range(start, start + count)),
               "eeg": eeg.tolist(), "fnirs": fnirs.tolist()}
    write_private_json(output, payload, force)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    model = subparsers.add_parser("model", help="Export six private checkpoints and the prior")
    model.add_argument("--checkpoint-dir", type=Path, default=ROOT / "checkpoints")
    model.add_argument("--output", type=Path, default=ROOT / "artifacts/browser/model.vtp-model.json")
    model.add_argument("--force", action="store_true")
    data = subparsers.add_parser("input", help="Prepare one local trial using the existing feature pipeline")
    data.add_argument("--data-root", type=Path, default=ROOT / "data/MER_PS_trainval")
    data.add_argument("--subject", default="test_1")
    data.add_argument("--video", type=int, default=1)
    data.add_argument("--start", type=int, default=0)
    data.add_argument("--count", type=int, default=60)
    data.add_argument("--output", type=Path, default=ROOT / "artifacts/browser/input.vtp-input.json")
    data.add_argument("--force", action="store_true")
    args = parser.parse_args()
    torch.set_num_threads(1)
    if args.command == "model":
        export_model(args.checkpoint_dir, args.output, args.force)
    else:
        export_input(args.data_root, args.subject, args.video, args.start, args.count, args.output, args.force)


if __name__ == "__main__":
    main()
