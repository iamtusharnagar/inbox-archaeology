"""Reads a real mbox file (the format Gmail Takeout and most other mail
exports use) using only the standard library's `mailbox` module, and turns
it into a deduplicated list of likely-forgotten accounts.

Never writes anything back to the mbox, never makes a network request, and
never needs anything beyond a local file path.
"""

from __future__ import annotations

import mailbox
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from .classifier import extract_domain, extract_service_name, is_signup_subject


@dataclass
class AccountRecord:
    domain: str
    service_name: str
    first_seen: datetime | None
    evidence_subject: str


def _get_header(message: mailbox.mboxMessage, name: str) -> str:
    value = message.get(name, "")
    return str(value) if value else ""


def _parse_date(message: mailbox.mboxMessage) -> datetime | None:
    """Parses the Date header, always returning a timezone-aware result.

    A Date header lacking a timezone offset is rare but real; without
    normalizing it, comparing it against a normal aware datetime elsewhere
    in the same mailbox raises TypeError. Naive dates are assumed UTC
    rather than dropped -- an approximate date is more useful here than no
    date at all, and this only affects sort order, not whether an account
    is detected.
    """
    date_header = _get_header(message, "Date")
    if not date_header:
        return None
    try:
        parsed = parsedate_to_datetime(date_header)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def scan_mbox(path: str) -> list[AccountRecord]:
    """Scans an mbox file and returns one record per distinct domain that
    sent at least one signup-looking email, keeping the earliest such email
    as evidence.

    Malformed individual messages are skipped rather than aborting the
    whole scan -- a single corrupted message in a mailbox with thousands of
    entries shouldn't lose every result found so far.
    """
    records: dict[str, AccountRecord] = {}

    box = mailbox.mbox(path, create=False)
    try:
        for message in box:
            try:
                subject = _get_header(message, "Subject")
                from_header = _get_header(message, "From")
                if not subject or not from_header:
                    continue
                if not is_signup_subject(subject):
                    continue

                domain = extract_domain(from_header)
                if domain is None:
                    continue

                sent_at = _parse_date(message)
                service_name = extract_service_name(from_header)

                existing = records.get(domain)
                if existing is None or (
                    sent_at is not None
                    and (existing.first_seen is None or sent_at < existing.first_seen)
                ):
                    records[domain] = AccountRecord(
                        domain=domain,
                        service_name=service_name,
                        first_seen=sent_at,
                        evidence_subject=subject,
                    )
            except Exception:
                # One malformed message (a broken Date header, unusual
                # encoding, etc.) shouldn't lose everything scanned so far.
                continue
    finally:
        box.close()

    return sorted(
        records.values(),
        key=lambda r: (r.first_seen is None, r.first_seen or datetime.min.replace(tzinfo=timezone.utc)),
    )
