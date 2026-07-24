"""Regression tests for the independent local-racing strategy.

Version: v2026.07.25.4
"""

from __future__ import annotations

import unittest

from local_shadow_strategy import evaluate_snapshot, format_discord


class LocalStrategyTest(unittest.TestCase):
    def base(self) -> dict:
        odds = {str(i): value for i, value in enumerate(
            [2.8, 4.0, 6.0, 12.0, 15.0, 18.0, 22.0, 25.0, 30.0, 35.0, 40.0, 50.0],
            start=1,
        )}
        pure = {
            "1": .28, "2": .27, "3": .10, "4": .11, "5": .06, "6": .04,
            "7": .03, "8": .025, "9": .025, "10": .02, "11": .02, "12": .02,
        }
        return {
            "p": pure, "o": odds, "h": {str(i): f"馬{i}" for i in range(1, 13)},
            "ages": {str(i): 4 for i in range(1, 13)},
            "past": {str(i): 6 for i in range(1, 13)},
        }

    def test_weak_favorite_first_position(self) -> None:
        result = evaluate_snapshot(self.base())
        self.assertEqual(result["action"], "SHADOW_BET")
        self.assertEqual(result["bet_type"], "三連単")
        self.assertEqual(result["rule"], "LONGSHOT_FIRST_WEAK_FAVORITE")
        self.assertEqual(len(result["tickets"]), 2)

    def test_all_two_year_old_is_no_bet(self) -> None:
        snap = self.base()
        snap["ages"] = {str(i): 2 for i in range(1, 13)}
        result = evaluate_snapshot(snap)
        self.assertEqual(result["action"], "NO_BET")

    def test_missing_odds_is_no_bet(self) -> None:
        result = evaluate_snapshot({"p": {"1": .5}, "o": {"1": 2.0}})
        self.assertEqual(result["action"], "NO_BET")

    def test_stake_matches_ticket_count(self) -> None:
        result = evaluate_snapshot(self.base())
        self.assertEqual(result["stake_yen"], 100 * len(result["tickets"]))

    def test_human_review_tickets_do_not_change_primary_bet(self) -> None:
        snap = self.base()
        result = evaluate_snapshot(snap)
        original = list(result["tickets"])
        message = format_discord("テスト1R", snap, result)
        self.assertEqual(result["tickets"], original)
        self.assertIn("人が判断する参考買い目", message)
        self.assertIn("参考・非推奨】単勝", message)

    def test_small_field_routes_axis_to_third(self) -> None:
        snap = self.base()
        snap["p"] = {key: value for key, value in snap["p"].items() if int(key) <= 8}
        total = sum(snap["p"].values())
        snap["p"] = {key: value / total for key, value in snap["p"].items()}
        snap["o"] = {key: value for key, value in snap["o"].items() if int(key) <= 8}
        snap["context"] = {
            "field_size": 8, "all_two_year": False, "cover3": .9, "avg_past": 5,
        }
        result = evaluate_snapshot(snap)
        self.assertEqual(result["rule"], "LONGSHOT_THIRD_SMALL_FIELD")
        self.assertTrue(all(ticket.endswith(f">{result['axis']}") for ticket in result["tickets"]))

    def test_large_quality_field_routes_to_sanfuku(self) -> None:
        snap = self.base()
        snap["o"]["1"] = 1.5
        snap["p"]["4"] = .16
        snap["p"]["1"] = .23
        snap["context"] = {
            "field_size": 12, "all_two_year": False, "cover3": .9, "avg_past": 5,
        }
        result = evaluate_snapshot(snap)
        self.assertEqual(result["rule"], "QUALITY_LARGE_FIELD_SANFUKU")
        self.assertEqual(result["bet_type"], "三連複")
        self.assertEqual(len(result["tickets"]), 1)

    def test_normal_favorite_never_restores_second_place_trifecta(self) -> None:
        snap = self.base()
        snap["o"]["1"] = 1.5
        snap["p"] = {key: value for key, value in snap["p"].items() if int(key) <= 10}
        snap["o"] = {key: value for key, value in snap["o"].items() if int(key) <= 10}
        snap["context"] = {
            "field_size": 10, "all_two_year": False, "cover3": .9, "avg_past": 5,
        }
        result = evaluate_snapshot(snap)
        self.assertEqual(result["rule"], "B_QUALITY_SANFUKU")
        self.assertEqual(result["confidence_tier"], "B")
        self.assertEqual(result["bet_type"], "三連複")


if __name__ == "__main__":
    unittest.main()
