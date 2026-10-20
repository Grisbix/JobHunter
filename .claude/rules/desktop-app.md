---
paths:
  - JobHunter.pyw
  - src/jobhunter/app/*.py
  - src/jobhunter/welcome.py
---
# Desktop application

Since phase 3.7, `JobHunter.pyw` is only the launcher: the app lives in
`src/jobhunter/app` — `fenetre.App` assembles one mixin per domain (`tableau`, `donnees`,
`fiche`, `actions`, `panneaux`, `detail`, `execution`). A setting rebound through `global`
(fonts, `theme` spacings) is read as `_theme.NOM`, never imported by copy.

**The table is indexed by position.** Removing a column requires removing *also*
the matching value in `_row_vals`, otherwise everything shifts by one.

The root comes from `jobhunter.root` (marker `data/` + `profil/`, or
`JOBHUNTER_RACINE`): the app works wherever it is placed. Never hard-code a root in it — the project's paths moved
four times in two days.

`_auto_scrape()` (2026-09-21) launches `scrape_jobs.py --headless` at startup
and on return of focus. Three safeguards, all necessary:

| Safeguard | Value | Why |
|---|---|---|
| `_bg_busy` lock | shared with `_auto_sync` | `job_sources.main()` holds the queue lock for the whole scan |
| `_SCRAPE_COOLDOWN_S` | 1800 s | without it, every click on the window relaunched a scan |
| session cap | 4 | bounds the cost of a day of back-and-forth |

Without them, a simple return of focus could freeze the app for the length of a full scan.

## A `.pyw` never says why it does not open

The `.pyw` extension suppresses the console: an exception at startup closes the window without
a word. To diagnose, relaunch with the **console** interpreter and read the trace:

```bash
PYTHONIOENCODING=utf-8 python JobHunter.pyw
```

Measured on 2026-09-22: the app had not opened since 20/09 17:27, and commit
`85e5d58c` — the very one that added `_auto_scrape` — had lost its
`def _auto_scrape(self):` line. The method body, indented by eight spaces, had been
absorbed by `_on_focus_scrape` just above. **The file compiled without error**:
`py_compile` passes, the attribute is only missing at runtime.

Corollary: after any edit of this file, check that every `self._methode`
called exists as a `def` of the `App` class, then **run the app** — compilation
proves nothing here.

## Layout "↶ Retour" (Back) (Alt+Left)

`_dispo_pile` remembers the layout **before** each gesture: table | card separator,
column width (`_dispo_suivre` on press/release), "Agrandir" (Enlarge) the card, Tools bar.
`_dispo_retour` goes back one gesture. Any new enlarging gesture calls
`_dispo_memo()` before acting. The content (statuses) falls under Ctrl+Z, not this stack.

## Statuses that hide, statuses that grey out

The Lieu (Location) column displays `zones.ville_affichee` (IDF = "Paris"), the Pays (Country) column `zones.pays_lieu`; `_sortkey` sorts on those same values.

`pas intéressé` (not interested) and `expiré` (expired) **hide** the row (`MASQUANTS`, "Voir les
masquées" (Show hidden) switch to see it again), `mauvaise` (bad) **greys it out**. `expiré` = closed posting, a fact,
not a judgement: do not confuse it with `mauvaise` or `refus` (rejection). Both live in `applications.json`; neither removes the offer from
the queue — that is the role of "Écarter" (Discard), which goes through `exclusions.py`. Any new
status goes into `STATUTS`, `ST_EMOJI` and, if it colours the row, `ST_COULEUR`.
Tracking is written through `suivi_io` (status key: **`s`**, not `statut` — the Stats
panel counted 0 applied for 10 applications, on 2026-09-23, because of that confusion).

A dialog is parented to **`self.root`**, never to `self`: `App` is not a widget.
`Toplevel(self)` compiles, and raises on click — "Écarter" did not open, observed and
fixed on 2026-09-23.

## Checking visually without launching a scan

`JOBHUNTER_SANS_FOND=1` turns off scan, descriptions and sync; `JOBHUNTER_ACTION` (together with the
previous one) runs Python in the app 1.5 s after opening, `app` designating the
instance — to get to a panel before a screenshot.
