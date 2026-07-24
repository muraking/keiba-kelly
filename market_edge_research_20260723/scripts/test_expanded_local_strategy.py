"""Regression tests for the expanded local B-tier rule.

Version: v2026.07.25.1
"""

from __future__ import annotations

import unittest

from local_shadow_strategy import evaluate_snapshot


class ExpandedLocalStrategyTest(unittest.TestCase):
    def snapshot(self) -> dict:
        return {
            "p": {
                "1": .22, "2": .21, "3": .12, "4": .11, "5": .10,
                "6": .07, "7": .05, "8": .04, "9": .035, "10": .025,
                "11": .01, "12": .01,
            },
            "o": {
                "1": 2.2, "2": 4.0, "3": 6.0, "4": 8.0, "5": 14.0,
                "6": 18.0, "7": 22.0, "8": 28.0, "9": 35.0,
                "10": 45.0, "11": 60.0, "12": 80.0,
            },
            "ages": {str(i): 4 for i in range(1, 13)},
            "past": {str(i): 6 for i in range(1, 13)},
            "context": {
                "field_size": 12, "all_two_year": False,
                "cover3": .9, "avg_past": 6.0,
            },
        }

    def test_b_tier_is_labeled_and_single_ticket(self) -> None:
        snapshot = {
            "p": {
                "1": .28, "2": .27, "3": .10, "4": .11, "5": .06,
                "6": .04, "7": .03, "8": .025, "9": .025, "10": .02,
            },
            "o": {
                "1": 1.5, "2": 4.0, "3": 6.0, "4": 12.0, "5": 15.0,
                "6": 18.0, "7": 22.0, "8": 25.0, "9": 30.0, "10": 35.0,
            },
            "ages": {str(i): 4 for i in range(1, 11)},
            "past": {str(i): 6 for i in range(1, 11)},
        }
        snapshot["context"] = {
            "field_size": 10, "all_two_year": False,
            "cover3": .9, "avg_past": 5.0,
        }
        result = evaluate_snapshot(snapshot)
        self.assertEqual(result["rule"], "B_QUALITY_SANFUKU")
        self.assertEqual(result["confidence_tier"], "B")
        self.assertEqual(result["bet_type"], "三連複")
        self.assertEqual(len(result["tickets"]), 1)

    def test_b_tier_rejects_short_history(self) -> None:
        snapshot = self.snapshot()
        snapshot["context"]["field_size"] = 10
        snapshot["context"]["avg_past"] = 4.9
        snapshot["p"] = {k: v for k, v in snapshot["p"].items() if int(k) <= 10}
        snapshot["o"] = {k: v for k, v in snapshot["o"].items() if int(k) <= 10}
        total = sum(snapshot["p"].values())
        snapshot["p"] = {k: v / total for k, v in snapshot["p"].items()}
        self.assertNotEqual(
            evaluate_snapshot(snapshot).get("rule"), "B_QUALITY_SANFUKU"
        )


if __name__ == "__main__":
    unittest.main()
