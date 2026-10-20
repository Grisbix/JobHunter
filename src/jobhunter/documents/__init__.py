"""Application documents: CV, letter, short message (phase 3.5 of the plan).

commun    cleaned title, skills, company values (shared)
cv        CV per offer (formerly tailor_application.tailor_cv, cv_une_page...)
lettre    cover letter (formerly tailor_application.tailor_letter...)
llm       optional rewriting by a local model
rendu     .docx -> .pdf
message   short message for forms (formerly Scripts/message_offre.py)
cv_auto   CV touch-ups from the fact bank (formerly Scripts/cv_auto.py)

FACADE (jobhunter._facade): `import tailor_application` gives this package, which sees
the names of commun, cv, lettre, llm and rendu like the old single file.
"""

from jobhunter import _facade

_MODULES = _facade.installer(__name__, ("common", "cv", "letter", "llm", "rendering"))
