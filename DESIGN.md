---
version: alpha
name: JobHunter
description: Desktop application (a web window, pywebview) that collects job offers, scores them against a profile and prepares the CV and letter for each one.
colors:
  fond-page: "#DDDBDA"
  carte: "#FFFFFF"
  surface: "#FFFFFF"
  encre: "#1C1917"
  texte-desc: "#3B3431"
  texte-doux: "#6F6763"
  gris: "#8A817C"
  gris-clair: "#B3AAA5"
  icone: "#B9B0AB"
  sombre: "#151312"
  sable: "#BFAEA4"
  tan: "#B68B70"
  rose: "#9B7362"
  c1: "#EAA476"
  c1b: "#E39A6C"
  c2: "#C98366"
  c3: "#A8766B"
  terre: "#B96D49"
  brun: "#5C3C2E"
  moyen1: "#D9C2B4"
  moyen2: "#B9A194"
  blob1: "#E9B48E"
  blob2: "#CFC6C4"
  blob3: "#F1D9C8"
typography:
  ui:
    fontFamily: Inter Display
  t-xs: 11px
  t-s: 12px
  t-m: 13px
  t-l: 14px
  t-xl: 16px
  t-2xl: 20px
  t-3xl: 24px
  t-4xl: 32px
  t-5xl: 44px
rounded:
  bouton: 12px
  carte: 14px
  panneau: 18px
spacing:
  panneau: 24px
  gap: 12px
---

## Overview

Frosted glass over a warm background: a page of soft colour blobs, panels of
translucent white (`--verre`, `--verre-fort`) edged with a white hairline (`--filet`),
the data on opaque cards (`carte`). Light by default, with a dark mode
(`:root.mode-sombre`). The reference is `src/jobhunter/web/static/style.css`: this file
follows it, never the reverse.

## Colors

- The accent family (`c1`, `c1b`, `c2`, `c3`, `terre`, `brun`, `moyen1`, `moyen2`,
  the blobs) is the « teinte » chosen in Réglages: terre (above, the default), vert,
  bleu, noir (`body[data-teinte=…]`). Each teinte redefines the whole family, its
  `-rgb` twins included; nothing else changes.
- Text: `encre` for content, `texte-desc` for descriptions, `texte-doux` and `gris`
  for secondary lines, `gris-clair` for placeholders only: as a label it reads at
  about 2:1 on the page.
- `sombre` is the filled button (`.bouton.plein`): the one main action of a screen.
- Dark mode redefines the neutrals and the glass from `--blanc-rgb`; the teinte keeps
  its accent.

## Typography

- One family: Inter Display, then Inter, Segoe UI Variable Display, Segoe UI, the
  system's. A family missing on the machine falls back down the list; never name one
  outside it.
- Sizes come from the scale `--t-xs` … `--t-5xl` only; body text is `t-l` (14 px).
- Weights 400 and 500; 600 for a rare emphasis in a line, never for a big figure or
  a title: size does the hierarchy.
- Sentence case: no labels in tracked capitals.

## Layout

- A navigation column on the left (folds to 64 px icons, `body.menu-replie`), the
  current view on the right, scrolling on its own.
- Panels have 24 px of padding; elements in a row are 8 to 12 px apart.
- Every screen holds at 1280 × 720 and at 900 × 560 without horizontal scrolling:
  rows wrap, they are not cut.
- **No empty areas, inside or outside the cards** (the user, 2026-11-04 and 11-05):
  - A grid row stretches every card to the tallest one. When the cards differ a lot in
    height (Réglages), lay them out in balanced columns at their own height
    (`.mosaique`, CSS columns, the tallest card first) rather than in a grid.
  - Two or three cards on a row: `.grille.ajustee` (auto-fit) so they share the whole
    row. A card spanning the row (`.large`) occupies every track and stops auto-fit from
    collapsing the empty one: put it outside that grid.
  - A list of short pairs (`.paires`) in a wide card: two pairs a line (`.paires.deux`).
  - An empty card or screen says what it is for and gives the way to fill it (a
    button), never a bare « — » or a blank card. An empty board (Candidatures) spreads
    its columns over the window, on one line.
- **No text against an edge.** Nothing within 8 px of its card's edge, nothing cut in
  two by its container:
  - A long list in a card scrolls inside the card (the list has the overflow, not the
    card), so the card keeps its padding; it fades out at its bottom (`mask-image`)
    with 24 px of padding for its last row to clear the fade.
  - A table cell stays a table cell (`td` never `display: flex`: it leaves the row's
    line and height); a column of buttons gets a fixed width in a `<colgroup>`.
  - `mask-image` only on a container without glass inside: on an ancestor of
    `backdrop-filter`, it would take the cards' blur away.
- Check: `uv run python tools/design_check.py --out captures` (every screen at 1440
  and 1000 px, `--vide` with no application), then look at the captures for empty
  space. `tests/test_design_layout.py` keeps the edge rule, Réglages' card heights and
  the empty Candidatures in CI.

## Shapes

- Buttons 40 px high, 12 px corners; cards 14 px; panels 18 px (the drawer and the
  dialogs too).
- A floating panel casts a small, soft shadow (`0 12px 32px -12px`, 22 %).
- A surface on another surface is not one more card: a row of buttons inside a card is
  a plain container, without border or corners.

## Motion and effects

- Blur and transitions go away under Remote Desktop (`body.leger`) and with
  `prefers-reduced-motion`.
- In the app window (`body.natif`) the glass is more opaque, so text stays readable
  over whatever is behind the window.

## Do's and Don'ts

- Do show a focus ring on everything Tab reaches (`:focus-visible`, 2 px `c2`); a
  mouse click draws none. Text fields keep their own glow.
- Do take colours from the variables, so that the teintes and dark mode follow.
- Don't name a font family outside the `--police` list.
- Do give a button the icon of what it does, from `ICONES` in app.js: collection
  `collecte` (arrow into a tray), daily schedule `horloge`, CV, letter or draft `plume`,
  a tool that runs `lancer`, the daily triage `entonnoir`, score `cible`, following
  `signet`, statistics `graphique`, adding `plus`.
- Don't use a decorative star or lightning bolt (the user, 2026-11-05): they say
  nothing about the button. `tests/test_design_scale.py` checks that every icon used
  exists and that neither comes back.
