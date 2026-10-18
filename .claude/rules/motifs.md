---
paths:
  - Scripts/ats_match.py
  - Scripts/job_sources.py
  - src/jobhunter/sources/*.py
  - Scripts/tri_file.py
  - src/jobhunter/scoring/*.py
  - src/jobhunter/texte.py
---
# Motifs regex — pièges mesurés

**Les regex ne s'écrivent pas via un heredoc shell.** `\b` y devient le caractère
backspace `\x08` ou un antislash littéral ; le motif compile, ne lève rien, et ne
matche plus jamais. Trois occurrences dans l'histoire du projet. Utiliser Write/Edit.

`jutil.verifier_motifs(globals())` s'exécute en fin de module dans `ats_match.py` et
`job_sources.py` : ils refusent de démarrer si un de leurs motifs est corrompu. Il
balaie **toute** `re.Pattern` du module, pas seulement celles préfixées `_RX_` — un
garde-fou qui choisit ses cibles par le nom finit par en rater.

**Attention aux sous-chaînes.** Famille de bugs la plus fréquente ici :
« sin**GAP**ore », « dive**RSE** », « **CLIMAT**isation », « trans**VERSE** »,
« **bp** dans BPCE ».

Inversement, un `\b` **final** sur un radical tue ses flexions : `sustainab\b` ne voit
pas « Sustainability », `alternan[ct]\b` ne voit pas « Alternance ».
**Les sigles gardent leurs deux bornes, les radicaux perdent la droite.**
