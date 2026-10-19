"""Proof of sending (navigation.confirmation): does the page confirm the application?

"Confirmé" requires a confirmation sentence or address AND a form that has disappeared;
everything else is "incertain" (ADR 0009). Nothing is ever clicked.
"""

import pytest

from jobhunter.navigation import confirmation as c

CONFIRMEES = [
    "Merci pour votre candidature ! Nous reviendrons vers vous rapidement.",
    "Votre candidature a bien été envoyée.",
    "Nous avons bien reçu votre candidature pour le poste d'analyste.",
    "Candidature envoyée avec succès",
    "Thank you for applying! Our team will review your profile.",
    "Your application has been submitted.",
    "Application received",
    "We've received your application and will be in touch.",
    "Vielen Dank für Ihre Bewerbung.",
    "Ihre Bewerbung wurde erfolgreich übermittelt.",
]
INCERTAINES = [
    # the form before sending talks about the application, without confirming it
    "Déposez votre candidature : CV, lettre de motivation.",
    "Postuler à cette offre — Envoyer ma candidature",
    "Merci de remplir tous les champs.",
    "Apply for this job",
    "",
]


@pytest.mark.parametrize("texte", CONFIRMEES, ids=[t[:30] for t in CONFIRMEES])
def test_phrase_de_confirmation(texte):
    etat, extrait = c.analyser_confirmation(texte, "https://ats.example/job/1", False)
    assert etat == c.CONFIRME and extrait


@pytest.mark.parametrize("texte", INCERTAINES, ids=[t[:30] or "vide" for t in INCERTAINES])
def test_pas_de_confirmation(texte):
    assert c.analyser_confirmation(texte, "https://ats.example/job/1", False)[0] == c.INCERTAIN


def test_formulaire_encore_la_jamais_confirme():
    texte = "Merci pour votre candidature ! Envoyer ma candidature"
    etat, raison = c.analyser_confirmation(texte, "https://ats.example/thank-you", True)
    assert etat == c.INCERTAIN and "formulaire" in raison


def test_message_d_erreur_l_emporte():
    texte = "Merci pour votre candidature. Ce champ est obligatoire : téléphone."
    etat, raison = c.analyser_confirmation(texte, "https://ats.example/job/1", False)
    assert etat == c.INCERTAIN and "erreur" in raison


@pytest.mark.parametrize(
    "url",
    [
        "https://jobs.example.com/apply/123/thank-you",
        "https://careers.example.fr/candidature/confirmation?id=9",
        "https://boards.example.io/acme/jobs/42/success",
    ],
)
def test_adresse_de_confirmation(url):
    assert c.analyser_confirmation("Acme", url, False)[0] == c.CONFIRME


@pytest.mark.parametrize(
    "url",
    [
        "https://thank-you-corp.example.com/jobs/42",  # the domain does not count
        "https://jobs.example.com/apply?next=/thank-you",  # nor does the query
        "https://jobs.example.com/successful-careers/42",  # longer word
    ],
)
def test_adresse_sans_confirmation(url):
    assert c.analyser_confirmation("Acme", url, False)[0] == c.INCERTAIN


# ── on a real page (local browser, set_content: no network) ───────────────
FORMULAIRE = (
    "<form><input name=nom><input name=mail type=email><input type=file>"
    "<button type=submit>Envoyer ma candidature</button></form>"
)


def test_page_de_merci_confirmee(page):
    page.set_content("<main><h1>Merci pour votre candidature !</h1></main>")
    r = c.observer_confirmation(page, attente=0.5, pas=0.1)
    assert r["etat"] == c.CONFIRME and "Merci pour votre candidature" in r["texte"]


def test_formulaire_toujours_affiche_incertain(page):
    page.set_content(FORMULAIRE)
    r = c.observer_confirmation(page, attente=0.3, pas=0.1)
    assert r["etat"] == c.INCERTAIN


def test_confirmation_qui_arrive_apres_un_delai(page):
    page.set_content(
        FORMULAIRE + "<script>setTimeout(() => { document.body.innerHTML ="
        " '<p>Your application has been submitted.</p>'; }, 400);</script>"
    )
    r = c.observer_confirmation(page, attente=3, pas=0.1)
    assert r["etat"] == c.CONFIRME


def test_observer_ne_clique_rien(page):
    page.set_content(FORMULAIRE.replace("<button", "<button onclick=\"document.title='clique'\""))
    c.observer_confirmation(page, attente=0.3, pas=0.1)
    assert page.title() != "clique"


def test_capture_de_preuve(page, tmp_path):
    page.set_content("<p>Merci pour votre candidature</p>")
    chemin = c.capturer_preuve(page, tmp_path / "preuves" / "x.png")
    assert chemin and (tmp_path / "preuves" / "x.png").stat().st_size > 0
