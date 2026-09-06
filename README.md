# inbox-archaeology

Find the accounts you've forgotten you have, from an email export you
already control. Entirely offline.

```
$ inbox-archaeology takeout-mbox/All\ mail\ Including\ Spam\ and\ Trash.mbox
Found 4 likely accounts from signup-looking emails in this mailbox:

- Spotify (spotify.com) -- first seen 2019-01-03
    based on: "Welcome to Spotify!"
- Notion (notion.so) -- first seen 2020-02-14
    based on: "Confirm your email to finish signing up"
- Duolingo (duolingo.com) -- first seen 2021-06-22
    based on: "Verify your email to activate your account"
- Random Forum (obscureforum.net) -- first seen 2021-06-28
    based on: "Welcome to Obscure Forum, please verify your account"

This is a best-effort guess, not a confirmed list...
```

## Why this exists

Every existing tool for finding "what accounts do I even have" either wants
OAuth access to your live inbox (a real company's server reading your real,
current email to build this list — a significant thing to hand over just to
find old accounts), or is a static directory of "here's how to delete your
Facebook"-style links that has no idea what accounts you specifically have.

This works from data you already have and control: an export of your own
mail. Google's Takeout tool produces one in `.mbox` format. This scans it
locally, offline, and produces a list. Nothing is uploaded. There is no
server. You can read all four source files and confirm there's no network
code anywhere in them.

## Install

```bash
pip install inbox-archaeology
```

Requires Python 3.10+. No other dependencies — parsing uses `mailbox` and
`email`, both part of the Python standard library.

## Get your export

[Google Takeout](https://takeout.google.com) → select only Mail → export.
You'll get a `.mbox` file, often quite large. This tool only reads it, never
modifies it.

## Use

```bash
inbox-archaeology path/to/your-export.mbox
inbox-archaeology path/to/your-export.mbox -o report.txt   # write to a file
```

## What it looks for

Subject lines that look like a new account was created — "Welcome to X",
"Verify your email", "Confirm your account", "Thanks for joining" — while
specifically excluding subjects that use similar words for a different
reason: password resets, login alerts, two-factor codes, email-change
confirmations, receipts, and unsubscribe confirmations. When a subject
matches both a signup pattern and an exclusion pattern (an unusual but real
case — "Welcome back, reset your password to continue"), the exclusion
wins, since a security-relevant framing shouldn't be buried by a
coincidental "welcome" phrase.

Multiple emails from the same domain collapse into a single result,
keeping the earliest as evidence of when you likely signed up.

## What it deliberately does not do

- **It doesn't claim to be complete.** An email worded unusually won't
  match, and this tool will never see accounts you created without a
  confirmation email in this particular inbox (a different email address,
  a purely offline signup, an account from before this export's range).
- **It doesn't delete anything, and can't.** It only reads the mbox file
  and prints a report. What you do with that list — which accounts to
  actually go delete — is entirely your call.
- **It doesn't guess perfectly.** The service name is a best-effort read
  of the sender's display name or domain, not a verified company name.

## Verified, honestly

63 tests across three layers:

- Pure classification logic (`classifier.py`) — including deliberate
  false-positive testing against realistic non-signup emails: password
  resets, 2FA codes, login alerts, receipts, an ordinary personal email,
  a newsletter, and the ambiguous case where "welcome" and "password"
  appear in the same subject.
- The scanner (`scanner.py`) tested against **real mbox files**, built with
  Python's own `mailbox` module — not hand-crafted strings pretending to
  be mbox format. A real bug was caught this way: `email.utils.
  parsedate_to_datetime` can return a timezone-naive datetime when a
  message's Date header omits a timezone offset, and sorting that against
  a normal timezone-aware date from another message raised `TypeError`.
  Verified as a real bug by temporarily reverting the fix and watching the
  test fail with exactly that error, then restoring it. Now covered by a
  dedicated regression test.
- An end-to-end smoke test against an 11-message realistic mixed inbox
  (Spotify, Notion, GitHub, a personal email, an Amazon receipt, Duolingo
  with two separate signup-adjacent emails, a LinkedIn login alert, an
  obscure forum, a bank OTP, and a newsletter) correctly identified the 4
  real signups and correctly ignored all 7 non-signup emails.

## Contributing

```bash
git clone https://github.com/tusharnagar2002/inbox-archaeology.git
cd inbox-archaeology
python -m venv .venv && source .venv/bin/activate
pip install -e .
python -m unittest discover -s tests -v
```

## License

MIT
