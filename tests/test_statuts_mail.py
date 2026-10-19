"""Statuts depuis les courriels (G4) : la bonne candidature, le bon statut, rien sans accord."""

import json
import mailbox
from email.message import EmailMessage

import pytest

from jobhunter.courriels import lecture, statuts
from jobhunter.courriels.lecture import Courriel
from jobhunter.programmes import statuts_mail

SUIVI = {
    "Amundi|Analyste ESG": {"s": "postulé", "d": "2026-10-01", "n": "relancer lundi"},
    "BNP Paribas SA|Chargé de projets RSE": {"s": "postulé", "d": "2026-10-02"},
    "BNP Paribas SA|Analyste climat": {"s": "postulé", "d": "2026-10-03"},
    "Mirova|Stage ISR": {"s": "à postuler"},
    "Sycomore|Analyste": {"s": "entretien", "d": "2026-10-05"},
    "Natixis|Analyste": {"s": "refus", "d": "2026-10-06"},
}


def c(de="", sujet="", corps="", le="2026-10-15"):
    return Courriel(de=de, sujet=sujet, le=le, corps=corps)


@pytest.mark.parametrize(
    ("courriel", "attendu"),
    [
        (c("Amundi Recrutement <jobs@amundi.com>", "Votre candidature",
           "Nous regrettons de ne pas pouvoir donner suite."), "refus"),
        (c("Amundi <no-reply@amundi.com>", "Your application",
           "Unfortunately we decided to move forward with other candidates."), "refus"),
        (c("talent@amundi.com", "Bewerbung", "Leider müssen wir Ihnen eine Absage erteilen."),
         "refus"),
        (c("Amundi <rh@amundi.com>", "Entretien",
           "Nous souhaitons vous rencontrer, pouvez-vous indiquer vos disponibilités ?"),
         "entretien"),
        (c("Amundi <rh@amundi.com>", "Next steps",
           "We would like to invite you to an interview."), "entretien"),
    ],
    ids=["refus fr", "refus en", "refus de", "entretien fr", "entretien en"],
)  # fmt: skip
def test_statut_et_candidature(courriel, attendu):
    p = statuts.propositions([courriel], SUIVI)
    assert [(x.oid, x.propose) for x in p] == [("Amundi|Analyste ESG", attendu)]


def test_refus_l_emporte_sur_le_remerciement():
    m = c("Amundi <rh@amundi.com>", "Votre candidature",
          "Merci pour votre candidature. Malheureusement, elle n'a pas été retenue.")  # fmt: skip
    assert statuts.propositions([m], SUIVI)[0].propose == "refus"


def test_accuse_de_reception_seulement_avant_l_envoi():
    accuse = "Nous avons bien reçu votre candidature."
    p = statuts.propositions([c("Mirova <rh@mirova.com>", "Candidature", accuse)], SUIVI)
    assert [(x.oid, x.propose) for x in p] == [("Mirova|Stage ISR", "postulé")]
    # déjà « postulé » : un accusé n'apporte rien
    assert statuts.propositions([c("Amundi <rh@amundi.com>", "Candidature", accuse)], SUIVI) == []


def test_jamais_en_arriere():
    entretien = c("Sycomore <rh@sycomore.fr>", "", "Thank you for applying to Sycomore.")
    assert statuts.propositions([entretien], SUIVI) == []
    refus_puis_entretien = c("Natixis <rh@natixis.com>", "Interview", "Schedule a call")
    assert statuts.propositions([refus_puis_entretien], SUIVI) == []


def test_domaine_de_l_expediteur():
    m = c("Recruiting <noreply@bnpparibas.com>", "Chargé de projets RSE",
          "Unfortunately, your application was not successful.")  # fmt: skip
    assert statuts.propositions([m], SUIVI)[0].oid == "BNP Paribas SA|Chargé de projets RSE"


def test_deux_postes_meme_entreprise_sans_intitule_rien():
    m = c("BNP Paribas <rh@bnpparibas.com>", "Votre candidature", "Pas retenue.")
    assert statuts.propositions([m], SUIVI) == []


def test_entreprise_seulement_dans_le_corps_ne_suffit_pas():
    lettre_info = c("Newsletter <info@media.fr>", "La semaine ESG",
                    "Amundi annonce un fonds. Unfortunately markets fell.")  # fmt: skip
    assert statuts.propositions([lettre_info], SUIVI) == []
    precis = c("Workday <noreply@myworkday.com>", "Mise à jour",
               "Votre candidature Analyste ESG chez Amundi n'a pas été retenue.")  # fmt: skip
    assert statuts.propositions([precis], SUIVI)[0].oid == "Amundi|Analyste ESG"


def test_le_plus_avance_garde():
    a = c("Amundi <rh@amundi.com>", "Interview", "We invite you to an interview.", "2026-10-10")
    b = c("Amundi <rh@amundi.com>", "Suite", "Pas retenue, désolés.", "2026-10-20")
    assert [p.propose for p in statuts.propositions([b, a], SUIVI)] == ["refus"]


# ── lecture des exports ──────────────────────────────────────────────────────


def message(de, sujet, corps, html=False):
    m = EmailMessage()
    m["From"], m["Subject"], m["Date"] = de, sujet, "Thu, 15 Oct 2026 10:00:00 +0200"
    if html:
        m.set_content("<p>Nous <b>regrettons</b> de ne pas donner suite.</p>", subtype="html")
    else:
        m.set_content(corps)
    m.add_attachment(b"%PDF piege", maintype="application", subtype="pdf", filename="x.pdf")
    return m


def test_mbox_et_html(tmp_path):
    boite = mailbox.mbox(str(tmp_path / "Tous.mbox"))
    boite.add(message("Amundi <rh@amundi.com>", "Candidature", "", html=True))
    boite.close()
    (c1,) = list(lecture.depuis_mbox(tmp_path / "Tous.mbox"))
    assert c1.le == "2026-10-15"
    assert "regrettons" in c1.corps and "<b>" not in c1.corps and "PDF" not in c1.corps


def test_dossier_eml(tmp_path):
    (tmp_path / "a.eml").write_bytes(
        bytes(message("Amundi <rh@amundi.com>", "Hello", "Pas retenue."))
    )
    (c1,) = list(lecture.depuis_eml(tmp_path))
    assert c1.sujet == "Hello" and "Pas retenue." in c1.corps


def test_gmail_sans_client_explique(tmp_path):
    with pytest.raises(FileNotFoundError, match="OAuth"):
        list(lecture.depuis_gmail(tmp_path))


@pytest.fixture
def faux_google(monkeypatch):
    """google-auth-oauthlib simulé : un jeton, deux pages de résultats."""
    import base64
    import sys
    import types

    etat = {"portees": [lecture.PORTEE], "requetes": []}
    brut = base64.urlsafe_b64encode(bytes(message("Amundi <rh@amundi.com>", "S", "Pas retenue.")))

    class Cred:
        expired, refresh_token, valid = False, None, True

        @property
        def scopes(self):
            return etat["portees"]

        def to_json(self):
            return '{"jeton": "faux"}'

    class Rep:
        def __init__(self, d):
            self.d = d

        def raise_for_status(self):
            pass

        def json(self):
            return self.d

    class Session:
        def __init__(self, cred):
            pass

        def get(self, url, params=None, timeout=None):
            etat["requetes"].append((url, dict(params or {})))
            if url.endswith("/messages"):
                if (params or {}).get("pageToken"):
                    return Rep({"messages": [{"id": "b"}]})
                return Rep({"messages": [{"id": "a"}], "nextPageToken": "p2"})
            return Rep({"raw": brut.decode()})

    flow = types.SimpleNamespace(
        from_client_secrets_file=lambda f, s: types.SimpleNamespace(
            run_local_server=lambda port: Cred()
        )
    )
    mods = {
        "google": types.ModuleType("google"),
        "google.auth": types.ModuleType("google.auth"),
        "google.auth.transport": types.ModuleType("google.auth.transport"),
        "google.auth.transport.requests": types.SimpleNamespace(
            AuthorizedSession=Session, Request=object
        ),
        "google.oauth2": types.ModuleType("google.oauth2"),
        "google.oauth2.credentials": types.SimpleNamespace(
            Credentials=types.SimpleNamespace(from_authorized_user_file=lambda f, s: Cred())
        ),
        "google_auth_oauthlib": types.ModuleType("google_auth_oauthlib"),
        "google_auth_oauthlib.flow": types.SimpleNamespace(InstalledAppFlow=flow),
    }
    for nom, mod in mods.items():
        monkeypatch.setitem(sys.modules, nom, mod)
    return etat


def test_gmail_lecture_seule_pagine_et_garde_le_jeton(tmp_path, faux_google):
    (tmp_path / lecture.CLIENT).write_text("{}", encoding="utf-8")
    lus = list(lecture.depuis_gmail(tmp_path, jours=30))
    assert len(lus) == 2 and lus[0].sujet == "S"
    assert (tmp_path / lecture.JETON).exists()
    liste = [p for u, p in faux_google["requetes"] if u.endswith("/messages")]
    assert liste[0]["q"] == "newer_than:30d -in:sent"
    assert all(
        p.get("format") == "raw" for u, p in faux_google["requetes"] if not u.endswith("/messages")
    )


def test_gmail_jeton_trop_large_refuse(tmp_path, faux_google):
    (tmp_path / lecture.CLIENT).write_text("{}", encoding="utf-8")
    faux_google["portees"] = [lecture.PORTEE, "https://www.googleapis.com/auth/gmail.send"]
    with pytest.raises(PermissionError):
        list(lecture.depuis_gmail(tmp_path))
    assert not (tmp_path / lecture.JETON).exists()  # jamais gardé


def test_fenetre_de_l_app_s_ouvre(racine_tk):
    """La fenêtre « Statuts depuis mes courriels » se construit, sans rien lire ni écrire."""
    import queue
    import types

    from jobhunter.app import courriels as fenetre

    fenetre.ouvrir(types.SimpleNamespace(root=racine_tk, q=queue.Queue()))
    racine_tk.update()
    titres = [w.title() for w in racine_tk.winfo_children() if hasattr(w, "title")]
    assert "Statuts depuis mes courriels" in titres


# ── écriture : seulement ce qui est validé ──────────────────────────────────


@pytest.fixture
def suivi_jetable(tmp_path):
    f = tmp_path / "suivi.json"
    f.write_text(json.dumps(SUIVI, ensure_ascii=False), encoding="utf-8")
    return f


def test_valider_ecrit_seulement_oui(suivi_jetable):
    refus = c("Amundi <rh@amundi.com>", "Candidature", "Pas retenue.", "2026-10-15")
    accuse = c("Mirova <rh@mirova.com>", "Candidature", "Avons bien reçu", "2026-10-14")
    props = statuts.propositions([refus, accuse], SUIVI)
    reponses = iter(["o", "n"])
    assert statuts_mail.valider(props, lambda q: next(reponses), suivi_jetable) == 1
    s = json.loads(suivi_jetable.read_text(encoding="utf-8"))
    assert s["Amundi|Analyste ESG"]["s"] == "refus"
    assert s["Amundi|Analyste ESG"]["d"] == "2026-10-15"
    assert s["Amundi|Analyste ESG"]["n"] == "relancer lundi"  # la note reste
    assert s["Amundi|Analyste ESG"]["courriel"]["sujet"] == "Candidature"
    assert s["Mirova|Stage ISR"] == {"s": "à postuler"}  # refusée : intacte


def test_quitter_arrete_tout(suivi_jetable):
    props = statuts.propositions([c("Amundi <rh@amundi.com>", "x", "Pas retenue.")], SUIVI)
    assert statuts_mail.valider(props, lambda q: "q", suivi_jetable) == 0
    assert json.loads(suivi_jetable.read_text(encoding="utf-8")) == SUIVI


def test_suivi_change_entre_temps_rien_ecrit(suivi_jetable):
    props = statuts.propositions([c("Amundi <rh@amundi.com>", "x", "Interview invite you")], SUIVI)
    s = json.loads(suivi_jetable.read_text(encoding="utf-8"))
    s["Amundi|Analyste ESG"]["s"] = "refus"  # l'utilisateur l'a changé dans l'app
    suivi_jetable.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
    assert statuts_mail.valider(props, lambda q: "o", suivi_jetable) == 0
    assert (
        json.loads(suivi_jetable.read_text(encoding="utf-8"))["Amundi|Analyste ESG"]["s"] == "refus"
    )
