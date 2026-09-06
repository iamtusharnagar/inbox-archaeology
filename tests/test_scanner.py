"""Tests the scanner against real mbox files, built with Python's own
mailbox module -- not hand-crafted strings pretending to be mbox format.
mbox has real, easy-to-get-subtly-wrong quirks (the "From " line escaping
rule, exact header folding), and a mock or a hand-rolled fake format would
prove nothing about whether this code handles a real mailbox correctly.
"""

import mailbox
import shutil
import tempfile
import unittest
from email.message import EmailMessage
from pathlib import Path

from inbox_archaeology.scanner import scan_mbox


class ScannerTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="inbox-archaeology-test-"))
        self.addCleanup(shutil.rmtree, self.tmp_dir, ignore_errors=True)
        self.mbox_path = str(self.tmp_dir / "test.mbox")

    def _make_mbox(self, messages: list[dict]) -> None:
        """Builds a real mbox file. Each dict needs 'from', 'subject', and
        optionally 'date' and 'body'.
        """
        box = mailbox.mbox(self.mbox_path, create=True)
        try:
            box.lock()
            for spec in messages:
                msg = EmailMessage()
                msg["From"] = spec["from"]
                msg["To"] = "me@example.com"
                msg["Subject"] = spec["subject"]
                if "date" in spec:
                    msg["Date"] = spec["date"]
                msg.set_content(spec.get("body", "body text"))
                box.add(msg)
        finally:
            box.unlock()
            box.close()


class BasicDetectionTests(ScannerTestCase):
    def test_a_real_welcome_email_is_detected(self):
        self._make_mbox(
            [
                {
                    "from": "Spotify <no-reply@spotify.com>",
                    "subject": "Welcome to Spotify!",
                    "date": "Mon, 01 Jun 2020 10:00:00 +0000",
                }
            ]
        )

        results = scan_mbox(self.mbox_path)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].domain, "spotify.com")
        self.assertEqual(results[0].service_name, "Spotify")

    def test_an_ordinary_personal_email_produces_nothing(self):
        self._make_mbox(
            [
                {
                    "from": "Priya <priya@gmail.com>",
                    "subject": "Re: dinner plans",
                    "date": "Mon, 01 Jun 2020 10:00:00 +0000",
                }
            ]
        )

        results = scan_mbox(self.mbox_path)

        self.assertEqual(results, [])

    def test_a_password_reset_email_produces_nothing(self):
        self._make_mbox(
            [
                {
                    "from": "GitHub <noreply@github.com>",
                    "subject": "Reset your GitHub password",
                    "date": "Mon, 01 Jun 2020 10:00:00 +0000",
                }
            ]
        )

        results = scan_mbox(self.mbox_path)

        self.assertEqual(results, [])

    def test_an_empty_mbox_produces_nothing_not_an_error(self):
        self._make_mbox([])

        results = scan_mbox(self.mbox_path)

        self.assertEqual(results, [])


class DeduplicationTests(ScannerTestCase):
    def test_multiple_emails_from_the_same_domain_collapse_to_one_record(self):
        self._make_mbox(
            [
                {
                    "from": "Spotify <no-reply@spotify.com>",
                    "subject": "Welcome to Spotify!",
                    "date": "Mon, 01 Jun 2020 10:00:00 +0000",
                },
                {
                    "from": "Spotify <notifications@spotify.com>",
                    "subject": "Confirm your email to finish signing up",
                    "date": "Mon, 01 Jun 2020 10:05:00 +0000",
                },
            ]
        )

        results = scan_mbox(self.mbox_path)

        self.assertEqual(len(results), 1)

    def test_the_earliest_email_is_kept_as_evidence(self):
        self._make_mbox(
            [
                {
                    "from": "Spotify <no-reply@spotify.com>",
                    "subject": "Confirm your email to finish signing up",
                    "date": "Mon, 01 Jun 2020 10:05:00 +0000",
                },
                {
                    "from": "Spotify <no-reply@spotify.com>",
                    "subject": "Welcome to Spotify!",
                    "date": "Mon, 01 Jun 2020 09:00:00 +0000",  # earlier
                },
            ]
        )

        results = scan_mbox(self.mbox_path)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].evidence_subject, "Welcome to Spotify!")

    def test_different_domains_produce_separate_records(self):
        self._make_mbox(
            [
                {
                    "from": "Spotify <no-reply@spotify.com>",
                    "subject": "Welcome to Spotify!",
                    "date": "Mon, 01 Jun 2020 10:00:00 +0000",
                },
                {
                    "from": "Notion <team@mail.notion.so>",
                    "subject": "Welcome to Notion",
                    "date": "Tue, 02 Jun 2020 10:00:00 +0000",
                },
            ]
        )

        results = scan_mbox(self.mbox_path)

        domains = {r.domain for r in results}
        self.assertEqual(domains, {"spotify.com", "notion.so"})


class DateHandlingTests(ScannerTestCase):
    def test_results_are_sorted_by_earliest_date_first(self):
        self._make_mbox(
            [
                {
                    "from": "Later <no-reply@later.com>",
                    "subject": "Welcome to Later",
                    "date": "Wed, 03 Jun 2020 10:00:00 +0000",
                },
                {
                    "from": "Earlier <no-reply@earlier.com>",
                    "subject": "Welcome to Earlier",
                    "date": "Mon, 01 Jun 2020 10:00:00 +0000",
                },
            ]
        )

        results = scan_mbox(self.mbox_path)

        self.assertEqual([r.domain for r in results], ["earlier.com", "later.com"])

    def test_a_missing_date_header_does_not_crash_and_sorts_last(self):
        self._make_mbox(
            [
                {
                    "from": "NoDate <no-reply@nodate.com>",
                    "subject": "Welcome to NoDate",
                    # no "date" key at all
                },
                {
                    "from": "HasDate <no-reply@hasdate.com>",
                    "subject": "Welcome to HasDate",
                    "date": "Mon, 01 Jun 2020 10:00:00 +0000",
                },
            ]
        )

        results = scan_mbox(self.mbox_path)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[-1].domain, "nodate.com")  # sorts after the dated one

    def test_a_malformed_date_header_does_not_crash_the_whole_scan(self):
        self._make_mbox(
            [
                {
                    "from": "Broken <no-reply@broken.com>",
                    "subject": "Welcome to Broken",
                    "date": "this is not a real date",
                },
                {
                    "from": "Fine <no-reply@fine.com>",
                    "subject": "Welcome to Fine",
                    "date": "Mon, 01 Jun 2020 10:00:00 +0000",
                },
            ]
        )

        results = scan_mbox(self.mbox_path)

        self.assertEqual(len(results), 2)

    def test_a_date_header_with_no_timezone_offset_does_not_crash_when_compared_against_an_aware_date(self):
        # Regression test for a real bug caught during development: Python's
        # parsedate_to_datetime can return a naive datetime when the Date
        # header omits a timezone offset. Sorting a naive datetime against
        # an aware one from a normal email raises TypeError unless both are
        # normalized consistently.
        self._make_mbox(
            [
                {
                    "from": "NoTz <no-reply@notz.com>",
                    "subject": "Welcome to NoTz",
                    "date": "Mon, 01 Jun 2020 10:00:00",  # no offset
                },
                {
                    "from": "HasTz <no-reply@hastz.com>",
                    "subject": "Welcome to HasTz",
                    "date": "Tue, 02 Jun 2020 10:00:00 +0000",
                },
            ]
        )

        results = scan_mbox(self.mbox_path)  # must not raise TypeError

        self.assertEqual(len(results), 2)


class MissingFieldTests(ScannerTestCase):
    def test_a_message_with_no_subject_is_skipped(self):
        box = mailbox.mbox(self.mbox_path, create=True)
        box.lock()
        try:
            msg = EmailMessage()
            msg["From"] = "no-reply@example.com"
            msg.set_content("body")
            box.add(msg)
        finally:
            box.unlock()
            box.close()

        results = scan_mbox(self.mbox_path)

        self.assertEqual(results, [])

    def test_a_message_with_no_from_header_is_skipped(self):
        box = mailbox.mbox(self.mbox_path, create=True)
        box.lock()
        try:
            msg = EmailMessage()
            msg["Subject"] = "Welcome to Somewhere"
            msg.set_content("body")
            box.add(msg)
        finally:
            box.unlock()
            box.close()

        results = scan_mbox(self.mbox_path)

        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
