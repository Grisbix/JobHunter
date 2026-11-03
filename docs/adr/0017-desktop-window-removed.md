# 0017 — The desktop window removed; the web window is the application

Date: 2026-11-03. Status: accepted (3.77).

## Context

Since 3.29 the web window (`jobhunter.web`, pywebview) is the application: every page
of the customtkinter desktop window (`jobhunter.app`, 11,100 lines) moved there, the
guided application last (`jobhunter.web.guided`). The desktop window stayed as a
fallback when the web view could not open, and behind `jobhunter bureau`. Two windows
meant two copies of each panel's logic and texts, tests for both, and a fallback that
hid a broken installation behind an older interface.

## Decision

- `jobhunter.app` is removed, with `jobhunter bureau`, its tests, `tools/sweep_app.py`
  and the old-name aliases of its modules. Its icon moves to `jobhunter/assets/`.
- When the web window cannot open, `jobhunter.launch` says why in a message box
  (JobHunter.pyw has no console) and how to fix it, and exits 1. In the installer's CI
  (`JOBHUNTER_EXIGER_WEB`) it still exits 2 without a box.
- The first launch's window (`jobhunter.welcome`, `welcome_tour`) stays in
  customtkinter: it runs before any profile exists, and the web window needs one. So
  `customtkinter` and `tkinterdnd2` stay dependencies until it moves into the web
  window.
- The locale catalogues (`jobhunter.locales`) stay: the web window reads them.

## Consequences

- One interface to keep in step; the architecture test now allows Tk only in
  `welcome`, `welcome_tour` and `launch`.
- Catalogue entries only the desktop window displayed are dead weight in
  `jobhunter.locales` until someone sorts them against the web window's texts.
- `DESIGN.md` was written from the desktop theme; `web/static/style.css` is the
  reference now.
