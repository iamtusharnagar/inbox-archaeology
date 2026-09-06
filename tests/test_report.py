import unittest
from datetime import datetime, timezone

from inbox_archaeology.report import format_report
from inbox_archaeology.scanner import AccountRecord


class FormatReportTests(unittest.TestCase):
    def test_empty_list_produces_a_clear_no_results_message(self):
        report = format_report([])
        self.assertIn("No likely account-signup emails were found", report)

    def test_singular_vs_plural_wording(self):
        one = [AccountRecord("a.com", "A", None, "Welcome to A")]
        two = [
            AccountRecord("a.com", "A", None, "Welcome to A"),
            AccountRecord("b.com", "B", None, "Welcome to B"),
        ]

        self.assertIn("Found 1 likely account from", format_report(one))
        self.assertIn("Found 2 likely accounts from", format_report(two))

    def test_includes_service_name_domain_and_evidence(self):
        records = [
            AccountRecord(
                "spotify.com",
                "Spotify",
                datetime(2020, 6, 1, tzinfo=timezone.utc),
                "Welcome to Spotify!",
            )
        ]

        report = format_report(records)

        self.assertIn("Spotify", report)
        self.assertIn("spotify.com", report)
        self.assertIn("2020-06-01", report)
        self.assertIn("Welcome to Spotify!", report)

    def test_a_missing_date_is_shown_as_date_unknown_not_blank_or_an_error(self):
        records = [AccountRecord("a.com", "A", None, "Welcome to A")]

        report = format_report(records)

        self.assertIn("date unknown", report)

    def test_includes_the_not_a_confirmed_list_caveat(self):
        records = [AccountRecord("a.com", "A", None, "Welcome to A")]

        report = format_report(records)

        self.assertIn("not a confirmed list", report)


if __name__ == "__main__":
    unittest.main()
