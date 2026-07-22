import tempfile
import unittest
from pathlib import Path

import numpy as np

from scripts.export_model_bundle import (
    DEFAULT_VARIANT,
    OUTPUT_DIR,
    append_manifest,
    parse_args,
    write_prior,
)


class ExportModelBundleTest(unittest.TestCase):
    def test_default_args_match_source_explicit_paper_configuration(self):
        args = parse_args([])
        self.assertEqual(OUTPUT_DIR, Path(__file__).resolve().parents[1] / "artifacts")
        self.assertEqual(DEFAULT_VARIANT, "source_explicit")
        self.assertEqual(args.output_dir, OUTPUT_DIR)
        self.assertEqual(args.checkpoint_dir, Path(__file__).resolve().parents[1] / "checkpoints")
        self.assertEqual(args.variant, DEFAULT_VARIANT)
        self.assertAlmostEqual(args.valence_weight, 0.99)
        self.assertAlmostEqual(args.arousal_weight, 0.92)
        self.assertEqual(args.bias_mode, "subject")
        self.assertAlmostEqual(args.bias_shrink_valence, 0.0)
        self.assertAlmostEqual(args.bias_shrink_arousal, 0.0)

    def test_append_manifest_uses_lf_line_endings(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.csv"
            append_manifest(path, [{"bundle": "candidate.zip", "variant": "candidate"}])
            content = path.read_bytes()
            self.assertNotIn(b"\r\n", content)
            self.assertEqual(content.count(b"\n"), 2)

    def test_write_prior_stores_weights_zero_shrink_and_variant(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.npz"
            output = root / "output.npz"
            np.savez_compressed(
                source,
                values=np.zeros((2, 2, 2), dtype=np.float32),
                blend_weights=np.asarray([0.5, 0.5], dtype=np.float32),
            )

            write_prior(
                source,
                output,
                prior_weights=np.asarray([0.99, 0.92], dtype=np.float32),
                bias_shrink=np.asarray([0.0, 0.0], dtype=np.float32),
                bias_mode="subject",
                variant="source_explicit",
            )

            with np.load(output, allow_pickle=False) as data:
                np.testing.assert_allclose(data["blend_weights"], [0.99, 0.92])
                np.testing.assert_allclose(data["baseline_bias_shrink"], [0.0, 0.0])
                self.assertEqual(str(data["baseline_bias_mode"].item()), "subject")
                self.assertEqual(str(data["analysis_variant"].item()), "source_explicit")

    def test_write_prior_keeps_scalar_shrink_compatible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.npz"
            output = root / "output.npz"
            np.savez_compressed(source, values=np.zeros((1, 1, 2), dtype=np.float32))

            write_prior(
                source,
                output,
                prior_weights=np.asarray([0.99, 0.92], dtype=np.float32),
                bias_shrink=0.0,
                bias_mode="subject",
            )

            with np.load(output, allow_pickle=False) as data:
                self.assertEqual(data["baseline_bias_shrink"].shape, ())
                self.assertAlmostEqual(float(data["baseline_bias_shrink"]), 0.0)


if __name__ == "__main__":
    unittest.main()
