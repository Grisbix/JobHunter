# 0013 — Several profiles: one workspace each

**Status**: accepted on 2026-10-20 (JobHunter 3.2.0).

## Context

One installation ran one search: one profile (`profile/profile.json`), one queue, one
tracking file. Running a second search — another job, another city, a relative's search on
the same computer — meant a second installation.

Every data path is built when its module is imported (`root.racine()`, `paths.py` and
about fifty module constants), and the queue, the tracking file and the lock are
single files. Three designs were possible:

- **one queue, offers tagged with a profile**: every reader of the queue, the
  tracking, the documents and the scoring would need a filter; one missed filter
  mixes two searches, and an application sent for one profile shows in the other;
- **hot switch of the paths**: re-pointing fifty constants at run time, in a GUI
  that keeps references to them, is a partial switch waiting to happen;
- **one complete data folder per profile**, the same layout as the main one.

## Decision

- **A profile is a complete data root**: `data/`, `profile/`, `My_CV/`, `CV/`,
  `Letters/` (always in the 3.0 layout). The installation's own folder is the main
  profile and nothing in it moves; the others live in `profiles/<slug>/`.
- **The slug is the identifier**: built once from the name, never a path
  (`[a-z0-9-]`, checked when read back), never changed. The displayed name lives in the
  profile (`_profil_nom`) and can change.
- **The active profile** is written in the main data folder
  (`_active_profile.json`) and applied at start-up by `profiles.appliquer()`, before
  any module builds a path: `JOBHUNTER_RACINE` points to the workspace,
  `JOBHUNTER_PRINCIPALE` remembers the main root. Child processes inherit both, so a
  task keeps the profile it started with even if the user switches meanwhile.
- **Switching profile restarts the application.** No hot switch.
- **Shared, never copied**: the API keys and Gmail access (`root.dossier_cles()`, the
  main data folder) and the browser profile. Copied once at creation as a starting
  point: the company lists (`sources_config.json`) and the interface settings.
- **The morning pipeline runs every profile**, one after the other, each in its own
  process with its own root, log and lock (`daily_pipeline.tous_les_profils`). The
  scheduled task is unchanged.
- **Creation** reuses the guided first launch (`first_launch <cv>`) inside the new
  workspace; an unfinished questionnaire leaves no profile behind.

## Consequences

- Two searches cannot mix: separate queues, tracking files, documents and locks.
- The keys' quotas are shared by every profile that collects with them.
- Profiles organise data; they are not a security boundary between people using the
  same system account.
- `jobhunter update` protects `profiles/` like the rest of the user data.
- A future "rename" or "archive" only touches `_profil_nom` or moves a folder; the
  slug, and the paths inside the workspace, stay valid.
