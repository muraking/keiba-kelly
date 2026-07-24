"""Regression tests for the JRA shadow decision rules.

Version: v2026.07.25.1
"""

from __future__ import annotations

import unittest

from jra_shadow_strategy import evaluate_snapshot


VERSION = "v2026.07.25.1"


def snapshot(axis_odds: float, axis_probability: float, field: int = 12) -> dict:
    odds = {str(i): float(2 + i) for i in range(1, field + 1)}
    odds["4"] = axis_odds
    probability = {str(i): 0.55 / (field - 1) for i in range(1, field + 1)}
    probability["4"] = axis_probability
    probability["1"] = 0.25
    probability["2"] = 0.22
    total = sum(probability.values())
    probability = {key: value / total for key, value in probability.items()}
    return {
        "p": probability,
        "o": odds,
        "h": {str(i): f"馬{i}" for i in range(1, field + 1)},
        "w": True,
        "t": "12:00",
    }


class StrategyTest(unittest.TestCase):
    def test_missing_odds_is_no_bet(self) -> None:
        result = evaluate_snapshot({"p": {"1": 1.0}, "o": {}})
        self.assertEqual(result["action"], "NO_BET")

    def test_never_returns_unknown_action(self) -> None:
        result = evaluate_snapshot(snapshot(12.0, 0.18))
        self.assertIn(result["action"], {"NO_BET", "SHADOW_BET"})

    def test_ticket_stake_matches_ticket_count(self) -> None:
        result = evaluate_snapshot(snapshot(8.0, 0.20))
        if result["action"] == "SHADOW_BET":
            self.assertEqual(result["stake_yen"], 100 * len(result["tickets"]))

    def test_fixed_sanfuku_rule_returns_three_tickets(self) -> None:
        odds = {
            "1": 3.0, "2": 5.0, "3": 8.0, "4": 12.0,
            "5": 14.0, "6": 16.0, "7": 20.0, "8": 22.0,
            "9": 25.0, "10": 28.0, "11": 32.0, "12": 40.0,
        }
        pure = {
            "1": 0.25, "2": 0.23, "3": 0.10, "4": 0.16,
            "5": 0.045, "6": 0.04, "7": 0.035, "8": 0.03,
            "9": 0.03, "10": 0.03, "11": 0.025, "12": 0.025,
        }
        result = evaluate_snapshot({
            "p": pure, "o": odds,
            "h": {str(i): f"馬{i}" for i in range(1, 13)},
            "w": True, "t": "12:00",
        })
        self.assertEqual(result["action"], "SHADOW_BET")
        self.assertEqual(result["bet_type"], "三連複")
        self.assertEqual(len(result["tickets"]), 3)
        self.assertEqual(result["stake_yen"], 300)


if __name__ == "__main__":
    unittest.main()
