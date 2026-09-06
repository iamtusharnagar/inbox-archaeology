"""The `inbox-archaeology` command."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .report import format_report
from .scanner import scan_mbox


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inbox-archaeology",
        description=(
            "Find the accounts you've forgotten you have, from an mbox email export "
            "you already control. Entirely offline -- reads the file, prints a report, "
            "makes no network request."
        ),
    )
    parser.add_argument("mbox_path", help="path to an .mbox file (e.g. from Google Takeout)")
    parser.add_argument("-o", "--output", help="write the report to a file instead of stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    path = Path(args.mbox_path)
    if not path.exists():
        print(f"error: {path} does not exist", file=sys.stderr)
        return 1
    if not path.is_file():
        print(f"error: {path} is not a file", file=sys.stderr)
        return 1

    try:
        records = scan_mbox(str(path))
    except Exception as error:
        print(f"error: could not read {path} as an mbox file: {error}", file=sys.stderr)
        return 1

    report = format_report(records)

    if args.output:
        Path(args.output).write_text(report + "\n")
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
