# 0009 — Proof of sending is distinct from the declaration

**Status**: accepted on 2026-10-19 (JobHunter 2.2.0).

## Context

Up to 2.1, an application moved to "postulé" (applied) when the user said so: a
keypress in the application program's console, then, a second time, a
confirmation in the app. Nothing kept a trace of what the site had displayed.
Yet a submission can fail silently: a required field forgotten, an expired session, a button
clicked twice. "I clicked Send" and "the site received my application" are two different
facts.

## Decision

- The send click remains the user's ([0005](0005-no-automatic-submission.md));
  they then **declare** it ("J'ai envoyé" (I have sent it) button in the app, or keypress in terminal
  mode).
- After the declaration, the program **observes** the page without clicking or typing anything, and
  writes to the tracking file, in a single operation: `s: "postulé"`, `envoi` and `preuve`.
  - `envoi: "confirmé"` only if the page shows a confirmation sentence
    ("Merci pour votre candidature", "Application submitted"…) or a confirmation
    address, **and** the form has disappeared.
  - `envoi: "incertain"` in all other cases: form still there, error
    message, silent page.
  - `envoi: "déclaré"` when the user confirms by hand, without observation.
  - `preuve`: the excerpt seen, the address, the date and a capture of the page
    (`Scripts/_preuves/`, local data).
- The status remains "postulé" in all three cases: follow-ups and metrics do not depend on it.
- "Incertain" **never** retries a submission: it is a signal to check, not an error
  to repair.
- A form that was filled in but not sent ("préparé") is not an application: it stays
  in the program's log (`apply_runner_done.json`), not in the tracking file.

## Consequences

The tracking file says what was observed, not only what was said. Detection is
deliberately cautious: an unusual confirmation page will yield "incertain",
never the reverse. The patterns live in `jobhunter/navigation/confirmation.py` and
are enriched with the pages actually encountered.
