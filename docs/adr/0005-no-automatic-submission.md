# 0005 — No automatic submission, no password handled

**Status**: accepted since the start of the project; not to be reopened in passing during a task.

## Context

Filling in an application form saves time; sending it in place of the
person commits their application without review, and exposes it to the automaton's mistakes.
Passwords for job sites give access to personal data.

## Decision

- Navigation fills in, uploads the documents and **highlights** the send button; the final
  click is always human. No `--auto` / `--submit` flag, and no send command in
  the CLI (tested).
- `login_flow` never types a password, whatever its argument (tested); the form
  profile never contains one.
- No automatic account creation; a code received by email is pasted, the "Vérifier" (Verify) button
  highlighted, and the human clicks.

## Consequences

Every application passes under its author's eyes. The time saved remains the essential part:
data entry.
