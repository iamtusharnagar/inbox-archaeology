"""Pure logic for recognizing "you created a new account" emails, and
telling them apart from emails that merely mention similar words for a
different reason (a password reset, a login alert, a receipt). Nothing
here touches a file or a mailbox -- see scanner.py for that -- so the part
where getting the classification wrong actually matters can be tested
directly and exhaustively.

This is a heuristic over the actual, wildly inconsistent way companies
write transactional email, not a parser for a real specification. It will
miss unusually-worded signup emails, and it will occasionally flag
something that isn't really a new account. See README.md for the honest
limitations.
"""

from __future__ import annotations

import re
from email.utils import parseaddr

# Checked in order; if a subject matches any of these, it's a candidate --
# but only after also checking that it doesn't match anything in
# EXCLUDE_PATTERNS, which takes priority. Order among SIGNUP_PATTERNS
# itself doesn't matter, only which set wins.
SIGNUP_PATTERNS = [
    re.compile(r"\bwelcome to\b", re.IGNORECASE),
    re.compile(r"\bwelcome aboard\b", re.IGNORECASE),
    re.compile(r"\bverify your (email|account)\b", re.IGNORECASE),
    re.compile(r"\bconfirm your (email|account)\b", re.IGNORECASE),
    re.compile(r"\bactivate your account\b", re.IGNORECASE),
    re.compile(r"\bplease confirm your\b", re.IGNORECASE),
    re.compile(r"\byour account (has been |is |was )?(created|set up)\b", re.IGNORECASE),
    re.compile(r"\bcomplete your (sign[\s-]?up|registration)\b", re.IGNORECASE),
    re.compile(r"\bfinish (setting up|creating) your account\b", re.IGNORECASE),
    re.compile(r"\bthanks for (signing up|joining|registering)\b", re.IGNORECASE),
]

# These take priority over SIGNUP_PATTERNS: an email matching one of these
# is never treated as a new-account signal, even if it also happens to
# contain a word like "verify" or "confirm".
EXCLUDE_PATTERNS = [
    re.compile(r"\bpassword\b", re.IGNORECASE),  # reset / changed / expiring
    re.compile(r"\bnew (sign[\s-]?in|login)\b", re.IGNORECASE),
    re.compile(r"\bsuspicious (login|activity|sign[\s-]?in)\b", re.IGNORECASE),
    re.compile(r"\bsecurity alert\b", re.IGNORECASE),
    re.compile(r"\btwo-factor\b|\b2fa\b|\bverification code\b|\bone-time (code|password)\b", re.IGNORECASE),
    re.compile(r"\byour (new )?email (address )?(has been |was )?changed\b", re.IGNORECASE),
    re.compile(r"\border confirmation\b|\breceipt\b|\binvoice\b", re.IGNORECASE),
    re.compile(r"\bunsubscribe(d)?\b", re.IGNORECASE),
]

# Subdomains commonly used for transactional mail, stripped before turning
# a domain into a human-readable guessed name. "mail.spotify.com" should
# suggest "Spotify", not "Mail".
TRANSACTIONAL_SUBDOMAIN_PREFIXES = (
    "mail.",
    "email.",
    "e.",
    "no-reply.",
    "noreply.",
    "notifications.",
    "notify.",
    "accounts.",
    "account.",
    "hello.",
    "info.",
    "mailer.",
    "mg.",  # Mailgun-hosted sending subdomains, e.g. mg.example.com
)


def is_signup_subject(subject: str) -> bool:
    """Whether a subject line looks like a new-account signal.

    Exclusions are checked first and win outright: a subject mentioning
    both "welcome" and "password" (e.g. a combined "welcome back, reset
    your password" email) is treated as NOT a signup signal, since the
    password-reset framing is the stronger, more specific signal here.
    """
    if any(pattern.search(subject) for pattern in EXCLUDE_PATTERNS):
        return False
    return any(pattern.search(subject) for pattern in SIGNUP_PATTERNS)


def registrable_domain(hostname: str) -> str:
    """Deliberately simple approximation (last two labels).

    Same documented limitation as second-look and is-this-phishing: not a
    real public-suffix-list implementation, good enough for the common
    case this tool targets.
    """
    parts = hostname.lower().split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else hostname.lower()


def strip_transactional_subdomain(hostname: str) -> str:
    """Strips a leading transactional-mail subdomain, if present.

    'mail.spotify.com' -> 'spotify.com'. Only strips one recognized prefix;
    'mail.notifications.spotify.com' is left with 'notifications.spotify.com'
    rather than looping, since chained transactional subdomains are rare
    enough that guessing further would risk stripping a real second-level
    label from a normal domain.
    """
    lower = hostname.lower()
    for prefix in TRANSACTIONAL_SUBDOMAIN_PREFIXES:
        if lower.startswith(prefix):
            return lower[len(prefix) :]
    return lower


def guess_name_from_domain(hostname: str) -> str:
    """Turns a domain into a human-readable guessed service name.

    'notifications.spotify.com' -> 'Spotify'. This is a guess, labeled as
    one in the report -- not presented as a confirmed company name.
    """
    stripped = strip_transactional_subdomain(hostname)
    domain = registrable_domain(stripped)
    label = domain.split(".")[0]
    return label.capitalize()


# A display name that's just the email address itself, or a handful of
# maximally-generic labels, isn't useful for identifying the service --
# fall back to guessing from the domain instead.
_GENERIC_DISPLAY_NAMES = {"", "noreply", "no-reply", "notifications", "notification", "mailer-daemon"}


def extract_service_name(from_header: str) -> str:
    """Extracts a human-readable service name from a raw From: header.

    Prefers the display name ('Spotify <no-reply@spotify.com>' -> 'Spotify')
    when it's present and not itself just a generic label, falling back to
    a domain-based guess otherwise.
    """
    display_name, email_address = parseaddr(from_header)
    display_name = display_name.strip().strip('"')

    if display_name and display_name.lower() not in _GENERIC_DISPLAY_NAMES and "@" not in display_name:
        return display_name

    hostname = email_address.split("@")[-1] if "@" in email_address else ""
    if not hostname:
        return "(unknown sender)"
    return guess_name_from_domain(hostname)


def extract_domain(from_header: str) -> str | None:
    """Extracts the registrable domain from a From: header, for deduplication."""
    _, email_address = parseaddr(from_header)
    if "@" not in email_address:
        return None
    hostname = email_address.split("@")[-1]
    return registrable_domain(strip_transactional_subdomain(hostname))
