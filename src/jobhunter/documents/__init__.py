"""Documents de candidature : CV, lettre, message court (phase 3.5 du plan).

commun    intitule nettoye, competences, valeurs d'entreprise (partages)
cv        CV par offre (ancien tailor_application.tailor_cv, cv_une_page...)
lettre    lettre de motivation (ancien tailor_application.tailor_letter...)
llm       reecriture optionnelle par un modele local
rendu     .docx -> .pdf
message   message court des formulaires (ancien Scripts/message_offre.py)
cv_auto   retouches de CV depuis la banque de faits (ancien Scripts/cv_auto.py)

FACADE (jobhunter._facade) : `import tailor_application` donne ce paquet, qui voit les
noms de commun, cv, lettre, llm et rendu comme l'ancien fichier unique.
"""

from jobhunter import _facade

_MODULES = _facade.installer(__name__, ("commun", "cv", "lettre", "llm", "rendu"))
