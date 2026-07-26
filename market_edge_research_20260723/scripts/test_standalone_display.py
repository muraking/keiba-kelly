"""Regression tests for independent-index display helpers.

Version: v2026.07.26.1
"""

from __future__ import annotations

import unittest

from standalone_display import (
    circled, circled_ticket, ev_circled, pace_lines, relative_styles,
)


class StandaloneDisplayTest(unittest.TestCase):
    def test_circled_horse_numbers_and_ticket(self) -> None:
        self.assertEqual(circled(1), "①")
        self.assertEqual(circled(18), "⑱")
        self.assertEqual(circled_ticket("3>12>7"), "③>⑫>⑦")
        self.assertEqual(ev_circled(1), "❶")
        self.assertEqual(ev_circled(12), "⓬")

    def test_relative_styles_cover_field(self) -> None:
        styles = relative_styles({
            "1": .10, "2": .20, "3": .35, "4": .50, "5": .70, "6": None,
        })
        self.assertEqual(styles["1"], "逃")
        self.assertEqual(styles["6"], "？")
        self.assertIn("展開 ", pace_lines({"s": styles})[0])


if __name__ == "__main__":
    unittest.main()
