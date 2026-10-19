"""Application statuses read in emails (step G4), read-only.

- `lecture`: the emails, from an export (Google Takeout .mbox, folder of .eml files)
  or the Gmail API, read-only (OAuth client created by the user, never a
  password);
- `statuts`: for each email, the tracked application it concerns and the status it
  suggests (acknowledgement, interview, rejection).

Nothing is written without validation, one suggestion at a time
(`programmes.statuts_mail`, or the application's window). An email is untrusted input:
it is only read and classified, never followed (no link opened, no attachment read).
"""
