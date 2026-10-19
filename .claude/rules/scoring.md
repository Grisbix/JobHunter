---
paths:
  - src/jobhunter/scoring/fit.py
  - src/jobhunter/scoring/tri.py
  - src/jobhunter/scoring/*.py
---
# Scoring — `ats_match.fit_score`

`fit_score(text, title)` returns an integer 1–10. Six weighted axes: ESG ×3, finance ×2,
AI ×1.5, data/risk/consulting ×1.

Three mechanisms you do not guess by reading the formula:

- **A cap proportional to ESG density.** Without it, finance + risk + consulting
  are enough to saturate the score without the slightest ESG signal. The cap follows the density
  of markers, not their mere presence: an 8000-character company description
  that says "sustainability" once is not an ESG offer. An explicitly ESG
  title lifts the cap to 10.
- **Language caps last** (`plafond_langue`): the profile's `langues_parlees`. A posting
  **written** in another language → 2 (stop words; the header counts separately, because EURES translates
  postings); a posting that **requires** a language not spoken → 4. "Dutch is a plus",
  "preferably Dutch", "Dutch and/or French", "Chinese markets" require nothing.
- **The classic financial analyst goes up to 8** (`_TITRE_FINANCE`, 2026-10-07): without ESG or
  AI, the general cap is 6, but a finance title (financial/investment/credit analyst,
  M&A, FP&A, contrôleur de gestion…) caps at 8 + 2 × ESG axis. ESG stays ahead.
- **Trade vetoes on the title**, which override any green vocabulary
  except a strong ESG-finance marker (`_ESG_TITRE_FORT`): HSE → 6; technical
  or non-finance trade (`_titre_hors_cible`: academic research, procurement, supply chain,
  construction, administrative, sciences) → 6, or 8 if the position mentions AI. A generic
  word — sustainab, durable, green, climat — would otherwise lift the cap of any
  trade. A technical title that names a financial trade (audit, analyst,
  credit) stays in the target.
- **Penalties apply to the TITLE only**, never to the description. Searched in
  the whole text, "Lead Generation" triggered the SENIOR penalty and "présence
  commerciale" the NEG penalty, i.e. −4 on an offer that is neither senior nor commercial.

**`fit_fin` breaks ties** (`fit_detail`, 2026-10-09): decimal, always within ±0.45 of the
integer `fit` — its rounding gives `fit`, no threshold moves. Within a level, `_departage`
weighs ESG title, ESG density, ESG/finance skills cited (uncapped), position of the
raw score, required experience. Any code that writes `fit` also writes `fit_fin`; the app,
the folders, top and alerts sort on it.

**The `fit` measures vocabulary density, not the accessibility of the position.** A
"2027 Corporate & Investment Bank" comes out at 6, an "AI Tech Lead" at 7. To sort
what really fits the profile, it is `tri_file.py` that decides — on the title and
the required experience.
