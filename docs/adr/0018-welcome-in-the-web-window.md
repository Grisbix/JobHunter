# 0018 — The welcome in the web window; no Tk left

Date: 2026-11-03. Status: accepted (3.78). Completes [0017](0017-desktop-window-removed.md).

## Context

After 3.77 the only customtkinter windows left were the first launch's: the welcome
(`jobhunter.welcome`: take back a previous folder, choose the CV, the profile form)
and its three-window tour (`welcome_tour`). They opened before the web window because
it needed a profile. Two looks, two toolkits, and the only reason `customtkinter` and
`tkinterdnd2` were still dependencies.

## Decision

- The web window opens without a profile. The page asks `bienvenue()` first
  (`jobhunter.web.onboarding`, mixed into `Api`); without a profile it draws the
  welcome instead of the application: take back a previous folder, or the CV (file
  dialog, or dropped on the window: pywebview gives the dropped file's full path to
  Python, which hands it to the page), then the form prefilled from it.
- Once the profile is written (or taken back) the window restarts on it: the data
  paths are fixed when the modules load, as for a profile switch (ADR 0013).
- `jobhunter.welcome` keeps the logic without a window (migration, take-back, the
  first_launch command line). Background work starts only once there is a profile.
- A new profile made from the application restarts the window in its empty folder,
  with the CV already chosen (`JH_CV`): the same welcome. « Plus tard » there archives
  the empty folder (never deletes it) and goes back to the main profile.
- The three-window tour is dropped: the home screen's « À faire » already points to
  the keys and the first collection.
- `customtkinter` and `tkinterdnd2` leave the dependencies, the requirements and the
  installer. Only `jobhunter.launch` still imports Tk, for its error box when the web
  view cannot open at all.

## Consequences

- One toolkit, one look; the architecture test allows Tk only in `launch`.
- The installer is smaller (no customtkinter themes, no native tkdnd library).
- An older pywebview without `webview.dom` loses the drop zone; the « Choisir mon CV… »
  button remains.
