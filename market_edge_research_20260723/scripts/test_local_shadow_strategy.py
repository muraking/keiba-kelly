"""Regression tests for local compact seven-minute notifications.

Version: v2026.07.27.1
"""

import unittest

from local_shadow_strategy import evaluate_snapshot, format_discord


class LocalStrategyTest(unittest.TestCase):
    def snapshot(self) -> dict:
        return {
            "p": {"1": .30, "2": .22, "3": .15, "4": .12, "5": .11, "6": .10},
            "q": {"1": .70, "2": .60, "3": .48, "4": .55, "5": .42, "6": .35},
            "o": {"1": 2.0, "2": 4.0, "3": 12.0, "4": 20.0, "5": 30.0, "6": 40.0},
            "h": {str(i): f"馬{i}" for i in range(1, 7)},
            "ages": {str(i): 4 for i in range(1, 7)},
            "past": {str(i): 6 for i in range(1, 7)},
            "r": 8,
            "d": 1800,
            "t": "12:00",
        }

    def test_compact_display_has_two_winners_and_three_holes(self) -> None:
        snap = self.snapshot()
        message = format_discord("大井8R", snap, evaluate_snapshot(snap))
        self.assertIn("勝1 ① 馬1", message)
        self.assertIn("勝2 ② 馬2", message)
        self.assertIn("穴1 ④ 馬4", message)
        self.assertIn("穴2 ③ 馬3", message)
        self.assertIn("穴3 ⑤ 馬5", message)
        self.assertNotIn("WP", message)
        self.assertNotIn("展開", message)

    def test_missing_odds_still_formats_all_race_notice(self) -> None:
        snap = self.snapshot()
        snap["o"] = {}
        message = format_discord("大井8R", snap, evaluate_snapshot(snap))
        self.assertIn("勝1 ① 馬1", message)
        self.assertIn("穴馬 未確定（オッズ未取得）", message)

    def test_local_middle_distance_candidate_is_added(self) -> None:
        snap = self.snapshot()
        snap["o"]["2"] = 4.0
        snap["o"]["4"] = 20.0
        message = format_discord("大井8R", snap, evaluate_snapshot(snap))
        self.assertIn("【検証候補】馬連 ②-④", message)


if __name__ == "__main__":
    unittest.main()
