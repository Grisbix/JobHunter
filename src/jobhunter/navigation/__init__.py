"""Navigation web (Playwright) : du site d'une societe jusqu'au formulaire rempli.

Ancien Scripts/web_nav.py (3 864 lignes), decoupe en phase 3.6 du plan :

page          bandeau cookies (REFUS d'abord), analyse de la page, attente du formulaire
etapes        boutons en deux temps, portails, menus, nouvelles tentatives
carrieres     page carriere d'une societe, puis l'offre dedans ; repli par la page d'accueil
formulaires   assistant multi-ecrans, depot des documents, remplissage de la candidature
segment       parties d'une page, ATS reconnu, bouton d'envoi SURLIGNE
compte        connexion par etapes (mot de passe JAMAIS tape), bascule vers l'inscription
linkedin      Easy Apply : remplit, l'humain envoie
llm           repli par modele local (Ollama) : vision, agent pas a pas
otp           code recu par courriel : colle, surligne Verifier, l'humain clique
navigateur    Playwright standard seul, aides de saisie, chargement robuste, session
categories    strategies par categorie de site ; leurs tableaux sont dans strategies

Captcha et anti-bot sont DETECTES pour passer la main a l'humain, jamais contournes ;
aucun moteur furtif. Le clic final d'envoi est toujours celui de l'utilisateur.

FACADE (jobhunter._facade) : `import web_nav` donne ce paquet, qui voit les noms de tous
les sous-modules comme l'ancien fichier unique.
"""

from jobhunter import _facade

_MODULES = _facade.installer(
    __name__,
    (
        "page",
        "etapes",
        "carrieres",
        "formulaires",
        "llm",
        "compte",
        "segment",
        "linkedin",
        "navigateur",
        "otp",
        "categories",
    ),
)
