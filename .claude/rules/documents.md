---
paths:
  - src/jobhunter/documents/**
  - src/jobhunter/programs/generate_docs.py
  - src/jobhunter/programs/regenerate_docs.py
  - src/jobhunter/programs/sync_docs.py
  - src/jobhunter/paths.py
  - src/jobhunter/paths.py
  - src/jobhunter/scoring/lexicon.py
  - src/jobhunter/documents/*.py
---
# Generated documents

`tailor_application.py` generates the CV and letter for one offer; `generate_docs.py` makes
batches of them from the queue. **The `.docx` is the source, the PDF derives from it** —
`sync_docs.py` is the enforcer of this rule.

`paths.py` is **the only place that decides where generated documents live**. Eleven
programs each built `ROOT / "CV" / "Par_offre"` on their own; taking them out
of the repository required eleven coordinated changes. Resolution cannot fail:
`data/chemins.json` if it exists, otherwise the project root.

The distinction that matters:

| Folder | Nature |
|---|---|
| `Par_offre/` | **output**, entirely rebuilt by `regenerate_docs.py` |
| `CV/Templates/`, `CV/Tailored/`, `Letters/Follow_ups/`, `Letters/Messages/`, `Letters/Tailored/` | **inputs** written by hand, which nothing regenerates |

`Letters/Tailored/<entreprise>__<poste>.txt` **replaces the body** of the letter for
that offer, paragraphs separated by a blank line. The template serves 5374 postings and
therefore cannot say anything precise about any of them; when an offer deserves an hour of work,
the body is written here.

Everything around it stays **generated** — header, date, subject line, salutation (which knows how to
name two recipients) and the matching closing line. What the code does better is not rewritten
by hand.

`CV/Tailored/<entreprise>__<poste>.json` adjusts the CV for that offer: `remplace`
(template text → text for the offer), `ajoute_apres`, `supprime` (to fit on one
page). An anchor that cannot be found is reported, never ignored. `generate_docs.py --url <extrait>`
redoes the CV and letter of an offer after an adjustment.

**Without a tailored version, the CV goes through `cv_auto`**, without an LLM: `CV/Facts.json` lists facts
validated by the user (`"valide": true`), with their triggers. A non-validated fact is
never used: nothing is invented. `cv_une_page()` regenerates by removing the `allegements`
(lightenings) one by one as long as the PDF exceeds one page, then starts again from the bare template as a last resort.
Any caller that produces a CV goes through `cv_une_page`, not through `tailor_cv` alone.
**A fact given for a single offer goes into its `CV/Tailored`, never into the bank**
without explicit agreement: Iberdrola and "advanced Spanish" (Helexia) had been put there by mistake.

The file lookup is tolerant of case and punctuation, and the key goes through
`_slug` **as a whole**. Joining two slugs around a literal `__` gave
`mirova__analyste…` against a file reduced to `mirova_analyste…`: the tailored letter
was never found, **without a message**, and the generic one went out in its place.

## Writing style

The register is set in the profile (`lettre`, `message`) and, for an offer that deserves
an hour, in `Letters/Tailored/`. A single rule is strong enough to live here.

## What a letter never says

**No sentence belittles the candidate.** Rule set by the user on 2026-09-22, after
seven rewrites of the same paragraph. Neither "my career is short but specialised", nor
"I am junior and I own it", nor "my professional experience is still short".

The fact remains true and the posting already knows it: it asks for a *first* experience.
Writing it down brings no information and takes away the reader's wish to go further. One
states what one brings, never what is missing.

The opposite move — boasting — is dealt with by the style rules above: no
superlative, no "rare specialisation", no judgement on the hiring market
("these two skills are rarely found together in one posting" explains the recruiter's own
job to them).

`check_repetitions.py` **catches none of this**. It counts repetitions, conjunctions
and semicolons; tone escapes it entirely, and it was green on all seven versions.
That is the reason `Letters/Tailored/` exists.

The `.docx` → PDF conversion goes through LibreOffice (`soffice.exe`), in **batches**: one
conversion at a time costs 1.2 s, most of which is the program's startup.
