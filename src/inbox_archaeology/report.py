"""Formats scan results into a plain-text report. Pure function, no I/O --
testable directly against constructed AccountRecord lists.
"""

from __future__ import annotations

from .scanner import AccountRecord


def format_report(records: list[AccountRecord]) -> str:
    if not records:
        return (
            "No likely account-signup emails were found in this mailbox.\n\n"
            "This could genuinely mean there weren't any, or it could mean this "
            "tool's patterns didn't match how your particular emails are worded. "
            "See the README for what it looks for."
        )

    lines = [
        f"Found {len(records)} likely account{'s' if len(records) != 1 else ''} "
        f"from signup-looking emails in this mailbox:",
        "",
    ]

    for record in records:
        date_str = record.first_seen.strftime("%Y-%m-%d") if record.first_seen else "date unknown"
        lines.append(f"- {record.service_name} ({record.domain}) -- first seen {date_str}")
        lines.append(f'    based on: "{record.evidence_subject}"')

    lines.append("")
    lines.append(
        "This is a best-effort guess, not a confirmed list. It can miss accounts "
        "worded unusually, and it can occasionally include something that wasn't "
        "really a new account. Use it as a starting point for your own review, "
        "not a final answer -- and consider deleting accounts you don't recognize "
        "or no longer use."
    )

    return "\n".join(lines)
