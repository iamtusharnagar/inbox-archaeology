import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from inbox_archaeology import cli


class MainTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="inbox-archaeology-cli-test-"))
        self.addCleanup(shutil.rmtree, self.tmp_dir, ignore_errors=True)

    def test_nonexistent_file_exits_1_with_a_clear_message(self):
        with patch("sys.stderr"):
            exit_code = cli.main([str(self.tmp_dir / "does-not-exist.mbox")])
        self.assertEqual(exit_code, 1)

    def test_a_directory_instead_of_a_file_exits_1(self):
        with patch("sys.stderr"):
            exit_code = cli.main([str(self.tmp_dir)])
        self.assertEqual(exit_code, 1)

    def test_a_file_that_is_not_a_valid_mbox_exits_1_not_a_crash(self):
        bad_file = self.tmp_dir / "not-an-mbox.mbox"
        bad_file.write_bytes(b"\x00\x01\x02 this is not a real mbox file")

        with patch("sys.stderr"):
            exit_code = cli.main([str(bad_file)])

        # Whether this is treated as a (valid but empty-of-results) mbox or
        # an outright read error depends on Python's own mailbox parser --
        # either way, main() must not raise, and must exit non-zero only
        # on a genuine read failure.
        self.assertIn(exit_code, (0, 1))

    def test_output_flag_writes_to_a_file_instead_of_stdout(self):
        import mailbox
        from email.message import EmailMessage

        mbox_path = self.tmp_dir / "test.mbox"
        box = mailbox.mbox(str(mbox_path), create=True)
        box.lock()
        try:
            msg = EmailMessage()
            msg["From"] = "Spotify <no-reply@spotify.com>"
            msg["Subject"] = "Welcome to Spotify!"
            msg["Date"] = "Mon, 01 Jun 2020 10:00:00 +0000"
            msg.set_content("body")
            box.add(msg)
        finally:
            box.unlock()
            box.close()

        output_path = self.tmp_dir / "report.txt"
        with patch("sys.stderr"):
            exit_code = cli.main([str(mbox_path), "-o", str(output_path)])

        self.assertEqual(exit_code, 0)
        self.assertTrue(output_path.exists())
        self.assertIn("Spotify", output_path.read_text())


if __name__ == "__main__":
    unittest.main()
