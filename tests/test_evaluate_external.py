import unittest

import numpy as np

from scripts.evaluate_external import (
    calculate_metrics,
    construct_stimulus_predictions,
    relative_time_bins,
    round_predictions,
)


class ExternalEvaluationTest(unittest.TestCase):
    def test_construct_stimulus_predictions_separates_global_video_and_time(self):
        rows = [
            {"subject": "p1", "video": 1, "timestamp": 0},
            {"subject": "p1", "video": 1, "timestamp": 1},
            {"subject": "p1", "video": 2, "timestamp": 0},
        ]
        values = np.full((3, 3, 2), np.nan, dtype=np.float32)
        values[1, :2] = [[10.0, 20.0], [30.0, 40.0]]
        values[2, :1] = [[90.0, 110.0]]
        prior = {
            "values": values,
            "video_lengths": np.asarray([0, 2, 1], dtype=np.int16),
            "global_values": np.asarray([50.0, 60.0], dtype=np.float32),
        }

        predictions = construct_stimulus_predictions(rows, prior)

        np.testing.assert_allclose(
            predictions["global_constant"],
            [[50.0, 60.0], [50.0, 60.0], [50.0, 60.0]],
        )
        np.testing.assert_allclose(
            predictions["video_identity"],
            [[20.0, 30.0], [20.0, 30.0], [90.0, 110.0]],
        )
        np.testing.assert_allclose(
            predictions["video_time"],
            [[10.0, 20.0], [30.0, 40.0], [90.0, 110.0]],
        )

    def test_calculate_metrics_matches_elementwise_mae_and_mse(self):
        target = np.asarray([[1.0, 2.0], [5.0, 8.0]])
        prediction = np.asarray([[2.0, 4.0], [3.0, 8.0]])

        metrics = calculate_metrics(prediction, target)

        self.assertAlmostEqual(metrics["overall_mae"], 1.25)
        self.assertAlmostEqual(metrics["valence_mae"], 1.5)
        self.assertAlmostEqual(metrics["arousal_mae"], 1.0)
        self.assertAlmostEqual(metrics["overall_mse"], 2.25)

    def test_relative_time_bins_use_each_trial_duration(self):
        rows = [
            {"subject": "p1", "video": 1, "timestamp": 0},
            {"subject": "p1", "video": 1, "timestamp": 1},
            {"subject": "p1", "video": 1, "timestamp": 2},
            {"subject": "p1", "video": 1, "timestamp": 3},
            {"subject": "p2", "video": 1, "timestamp": 0},
            {"subject": "p2", "video": 1, "timestamp": 1},
        ]

        bins = relative_time_bins(rows, bins=2)

        np.testing.assert_array_equal(bins, [0, 0, 1, 1, 0, 1])

    def test_round_predictions_matches_integer_output_contract(self):
        values = np.asarray([[0.1, 1.5], [254.6, 300.0]], dtype=np.float32)
        np.testing.assert_array_equal(round_predictions(values), [[1, 2], [255, 255]])


if __name__ == "__main__":
    unittest.main()
