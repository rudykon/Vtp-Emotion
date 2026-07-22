import unittest

import numpy as np

from merps.calibration import (
    aggregate_baseline_bias,
    apply_baseline_bias_correction,
    baseline_bias_array,
)


class BaselineCalibrationTest(unittest.TestCase):
    def test_apply_baseline_bias_correction_supports_per_dimension_shrink(self):
        rows = [
            {"subject": "test_1", "video": 1},
            {"subject": "test_1", "video": 2},
        ]
        model = np.asarray([[140.0, 120.0], [150.0, 110.0]], dtype=np.float32)
        bias = {("test_1", None): np.asarray([10.0, -5.0], dtype=np.float32)}

        corrected = apply_baseline_bias_correction(
            rows,
            model,
            bias,
            shrink=np.asarray([0.5, 0.0], dtype=np.float32),
        )

        np.testing.assert_allclose(corrected, [[135.0, 120.0], [145.0, 110.0]])

    def test_apply_baseline_bias_correction_rejects_invalid_shrink_shape(self):
        rows = [{"subject": "test_1", "video": 1}]
        model = np.asarray([[140.0, 120.0]], dtype=np.float32)
        bias = {("test_1", None): np.asarray([10.0, -5.0], dtype=np.float32)}

        with self.assertRaisesRegex(ValueError, "scalar or shape"):
            apply_baseline_bias_correction(rows, model, bias, shrink=[0.5, 0.0, 0.5])

    def test_baseline_bias_array_uses_trial_then_subject_then_zero(self):
        rows = [
            {"subject": "test_1", "video": 1},
            {"subject": "test_1", "video": 2},
            {"subject": "test_2", "video": 1},
        ]
        bias = {
            ("test_1", 1): np.asarray([3.0, 4.0], dtype=np.float32),
            ("test_1", None): np.asarray([5.0, 6.0], dtype=np.float32),
        }

        actual = baseline_bias_array(rows, bias)

        np.testing.assert_allclose(actual, [[3.0, 4.0], [5.0, 6.0], [0.0, 0.0]])

    def test_apply_baseline_bias_correction_uses_subject_bias(self):
        rows = [
            {"subject": "test_1", "video": 1},
            {"subject": "test_1", "video": 2},
            {"subject": "test_2", "video": 1},
        ]
        model = np.asarray([[140.0, 120.0], [150.0, 110.0], [160.0, 100.0]], dtype=np.float32)
        bias = {("test_1", None): np.asarray([10.0, -5.0], dtype=np.float32)}

        corrected = apply_baseline_bias_correction(rows, model, bias, shrink=0.5)

        np.testing.assert_allclose(corrected, [[135.0, 122.5], [145.0, 112.5], [160.0, 100.0]])

    def test_apply_baseline_bias_correction_can_use_trial_bias(self):
        rows = [
            {"subject": "test_1", "video": 1},
            {"subject": "test_1", "video": 2},
        ]
        model = np.asarray([[140.0, 120.0], [150.0, 110.0]], dtype=np.float32)
        bias = {
            ("test_1", 1): np.asarray([10.0, -5.0], dtype=np.float32),
            ("test_1", 2): np.asarray([-4.0, 8.0], dtype=np.float32),
        }

        corrected = apply_baseline_bias_correction(rows, model, bias, shrink=1.0)

        np.testing.assert_allclose(corrected, [[130.0, 125.0], [154.0, 102.0]])

    def test_scalar_shrink_exactly_matches_equal_vector_at_clipping_boundaries(self):
        rows = [
            {"subject": "test_1", "video": 1},
            {"subject": "test_1", "video": 2},
            {"subject": "test_1", "video": 3},
        ]
        model = np.asarray(
            [[1.0, 255.0], [1.5, 254.5], [255.0, 1.0]],
            dtype=np.float32,
        )
        bias = {("test_1", None): np.asarray([4.0, -4.0], dtype=np.float32)}

        scalar = apply_baseline_bias_correction(rows, model, bias, shrink=1.0)
        vector = apply_baseline_bias_correction(
            rows,
            model,
            bias,
            shrink=np.asarray([1.0, 1.0], dtype=np.float32),
        )

        np.testing.assert_array_equal(scalar, vector)
        np.testing.assert_array_equal(scalar, [[1.0, 255.0], [1.0, 255.0], [251.0, 5.0]])

    def test_aggregate_baseline_bias_supports_subject_and_trial_modes(self):
        rows = [
            {"subject": "test_1", "video": 1},
            {"subject": "test_1", "video": 2},
        ]
        baseline_pred = {
            ("test_1", 1): np.asarray([140.0, 120.0], dtype=np.float32),
            ("test_1", 2): np.asarray([130.0, 132.0], dtype=np.float32),
        }

        subject_bias = aggregate_baseline_bias(rows, baseline_pred, mode="subject")
        trial_bias = aggregate_baseline_bias(rows, baseline_pred, mode="trial")

        np.testing.assert_allclose(subject_bias[("test_1", None)], [7.0, -2.0])
        np.testing.assert_allclose(trial_bias[("test_1", 1)], [12.0, -8.0])
        np.testing.assert_allclose(trial_bias[("test_1", 2)], [2.0, 4.0])


if __name__ == "__main__":
    unittest.main()
