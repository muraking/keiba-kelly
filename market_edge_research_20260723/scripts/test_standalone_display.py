"""Regression tests for independent-index display helpers.

Version: v2026.07.26.2
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from standalone_display import (
    circled, circled_ticket, ev_circled, notification_due, pace_lines,
    relative_styles,
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

    def test_notifications_are_never_due_after_post(self) -> None:
        post = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)
        self.assertTrue(notification_due(post - timedelta(minutes=7), post, 7))
        self.assertTrue(notification_due(post - timedelta(seconds=1), post, 7))
        self.assertFalse(notification_due(post, post, 7))
        self.assertFalse(notification_due(post + timedelta(minutes=1), post, 30))


if __name__ == "__main__":
    unittest.main()
