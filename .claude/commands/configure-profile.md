---
description: Configure JobHunter for the user from their CV (complete, verified profile)
argument-hint: "[path to the CV .docx or .pdf]"
---

You are configuring JobHunter for the person who uses it. At the end, `profil/profil.json`
must be **complete**: the application must find, sort and prepare their applications
as well as it does for the example profile, but for THEIR profession.

Answer the user in their own language.

CV given: $ARGUMENTS

## Rules

- **Invent no fact.** Degrees, employers, figures, tools and languages come from the
  CV or from the user. What is missing, you ask for; otherwise you leave
  `"À COMPLÉTER"` and flag it at the end.
- No password, no API key: you do not ask for them and do not write them anywhere.
  For Adzuna and Jooble, the user creates their own keys (see README).
- No modification of the engine (`Scripts/*.py`): everything is set in the profile. If a
  need cannot be expressed there, say so instead of coding.
- Do not read `profil/exemple_finance_esg.json` in full in one go if it does not fit:
  read it section by section (`python -c "import json;print(json.dumps(json.load(open('profil/exemple_finance_esg.json',encoding='utf-8'))['scoring'],ensure_ascii=False,indent=1))"`).

## Steps

1. **The CV.** If it is not given above, ask for its path. Prefer a `.docx`:
   it is the template for all the CVs sent (a PDF is sent as is). Read its text:
   `python -c "import sys;sys.path.insert(0,'Scripts');import first_launch as p;print(p.lire_cv(__import__('pathlib').Path(r'CHEMIN')))"`.

2. **The questions**, in a single message, with your proposals drawn from the CV:
   - target professions (2 to 5 job titles, as they appear in postings);
   - years of experience, internships included;
   - contract type (CDI, CDD, internship, work-study, V.I.E, freelance);
   - cities or regions; abroad too?;
   - gender agreements in the letters: "diplômé" or "diplômée" (masculine or feminine "graduate");
   - professions or sectors to **exclude**;
   - the companies they target as a priority, if any.

3. **The skeleton.** Run (add `--force` if a profile exists, after agreement):
   ```bash
   python -m jobhunter profile "<cv>" --metiers "<m1, m2>" --annees <n> --genre <m|f> --prioritaires "<secteurs>" --secondaires "<secteurs>" --entreprises <o|n>
   ```
   Known sectors: `python -c "import sys;sys.path.insert(0,'Scripts');import zones;print(list(zones.CATALOGUE))"`.
   A city missing from the catalogue is declared in the profile's `zones`, as an object
   `{"cle", "libelle", "lieux", "departements"}` (example at the top of the
   "SECTEURS GEOGRAPHIQUES" section of `src/jobhunter/scoring/zones.py`).
   `--entreprises o` only if the person targets finance or ESG.

4. **The complete profile.** Compare `profil/profil.json` with the example, section by
   section, and fill in each one for this profession:
   - `domaines`: one per target profession. `mots_titre` = title words and variants
     (FR + EN, masculine + feminine), `parcours_fr`/`parcours_en` = 3 to 4 factual
     sentences drawn from the CV, `accroche_*` and `preuve_*` = one sentence each.
   - `competences`: one entry per skill in the CV, with the words that postings
     use to express it (synonyms, English, acronyms). Aim for 15 to 30 entries.
   - `termes`: the profession's acronyms and tools, in lowercase.
   - `scoring`: `axes` (skill families), `axe_coeur` = the core of the profession,
     `axe_complement` = what sets it apart; `intitules_coeur(_forts)` = titles
     that deserve 10; `intitules_hors_metier` = titles to cap low.
   - `niveau`: according to years of experience (`experience_max` = what they can aim for).
   - `filtre_titre`: `metier` = what a title must contain to be collected,
     `exclus` = what rules it out. Too narrow, no offers; too wide, noise.
   - `tri.metiers_exclus`: out-of-target families.
   - `collecte.mots_cles`: 8 to 15 searches, FR and EN if abroad is targeted.
   - `message` and `lettre`: degree, languages, profile sentence, facts per skill.
   A word list accepts `"mot"` or `"re:regex"`. Regexes are written with the editing
   tool, **never through a shell heredoc** (`\b` becomes a backspace there).

5. **Verify.**
   ```bash
   python -m jobhunter show-profile
   python -m jobhunter check-profile "<intitulé visé 1>" "<intitulé visé 2>" "<intitulé voisin hors cible>" "<intitulé senior du métier>"
   ```
   Expected: the target titles are `garde` (kept), in the right domain, with the highest
   score; the out-of-target ones are `ECARTE` (discarded) or scored low; the senior one is penalised if the
   person is junior. The score is computed on the title alone: a real offer,
   scored with its description, goes higher. Fix the profile and start again
   until it is right.
   Then a real trial, writing nothing: `python -m jobhunter collect --linkedin --dry`.
   Look at the titles kept: if they overflow or are missing, adjust `filtre_titre` and
   `collecte.mots_cles`.

6. **The report to the user**: what was filled in, what remains `À COMPLÉTER`, the
   choices made on their behalf, and what comes next: `python JobHunter.pyw`, then
   `python -m jobhunter pipeline` for the first full collection.
