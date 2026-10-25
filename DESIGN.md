---
version: alpha
name: JobHunter
description: Desktop application (Tkinter / CustomTkinter) that collects job offers, scores them against a profile and prepares the CV and letter for each one.
colors:
  bg: "#E9EFF7"
  work: "#F4F7FB"
  card: "#FFFFFF"
  line: "#D8E2EF"
  line-saisie: "#74869F"
  tx: "#19283F"
  mut: "#52647B"
  row0: "#FFFFFF"
  row1: "#F5F8FC"
  acc: "#325EDF"
  acc-h: "#234FC7"
  acc-tx: "#FFFFFF"
  focus: "#325EDF"
  ok: "#25704F"
  bad: "#AC3E49"
  purp: "#70549C"
  teal: "#246B76"
  ambre: "#8A5B19"
  side: "#172B50"
  side-card: "#223963"
  side-tx: "#F5F8FE"
  side-mut: "#C3D3EC"
  side-h: "#304C80"
  side-alerte: "#F6C467"
  btn: "#E7EDF7"
  btn-h: "#D4E1F7"
  del: "#FBECEF"
  del-h: "#F4DADF"
  del-tx: "#AC3E49"
typography:
  ui:
    fontFamily: IBM Plex Sans
  mono:
    fontFamily: IBM Plex Mono
rounded:
  btn: 6px
  card: 10px
spacing:
  pad-page: 20px
  gap: 12px
---

## Overview

A recruitment-CRM layout adapted to one person's job search: navy navigation on the
left, a pale blue workspace, the data on white. The application is light only.

## Colors

- The side bar uses its own set (`side`, `side-card`, `side-tx`, `side-mut`, `side-h`).
  The colours of the light surfaces are not reused on it: a warning there is
  `side-alerte`, because `ambre` is unreadable on navy.
- An input field's outline is `line-saisie`, which keeps at least 3:1 on `card`, `bg`
  and `work` (WCAG 1.4.11). `line` is for the borders of surfaces only.
- The keyboard focus ring is the accent (`focus`), on every background.
- A button's text colour follows its background role (`acc` → `acc-tx`, `del` →
  `del-tx`, the side bar → `side-tx`), so that a button can never be unreadable.
- Each button role has its own hover tint (`acc-h`, `btn-h`, `del-h`, `side-h`), never
  the toolkit's default blue.
- Table rows alternate `row0` and `row1`.

## Typography

- `ui` is IBM Plex Sans when installed, otherwise Segoe UI; `mono` is IBM Plex Mono,
  otherwise Cascadia Mono or Consolas. The family is resolved at start-up among the
  installed fonts: never name a family that may be missing, Tk then falls back to an
  arbitrary font.

## Layout

- Spacing is set once at start-up (`pad-page`, `gap`); it does not follow window
  resizes.

## Shapes

- A surface on another surface is not one more card: a row of buttons inside a card is a
  plain container, without border or corners.
- One border per surface (`line`, 1 px), only on a `card` placed on a different
  background; sub-containers get none.

## Do's and Don'ts

- Do make every button reachable and operable by keyboard (Tab, Enter, Space).
- Don't name a font family without checking it is installed.
- Don't put the amber of the light surfaces on the dark side bar.
