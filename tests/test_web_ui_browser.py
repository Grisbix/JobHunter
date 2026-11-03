"""The web window in a real headless Chromium, with the Python API MOCKED.

index.html and app.js load as they ship; `window.pywebview.api` is a stand-in that
answers from a table and records every call. What it checks is the JavaScript side
the Python tests cannot see: the welcome screens (3.78, ADR 0018) drawn from what
`bienvenue()` answers, the buttons calling the right API, and never a blank window.
"""

import json
from pathlib import Path

import pytest

INDEX = Path(__file__).resolve().parents[1] / "src" / "jobhunter" / "web" / "static" / "index.html"

# Every API method answers from `reponses` (null when absent); a value
# {"rejette": "..."} makes the call fail. Each call is kept in window.__appels.
_FAUX_PYWEBVIEW = """
window.__appels = [];
const reponses = %s;
window.pywebview = { api: new Proxy({}, { get: (_o, nom) => (...args) => {
  window.__appels.push([nom, ...args]);
  const r = reponses[nom];
  if (r && r.rejette) return Promise.reject(new Error(r.rejette));
  return Promise.resolve(r === undefined ? null : r);
} }) };
"""


@pytest.fixture
def fenetre(page):
    def ouvrir(**reponses):
        page.add_init_script(_FAUX_PYWEBVIEW % json.dumps(reponses))
        page.goto(INDEX.as_uri())
        return page

    return ouvrir


def appels(page, nom):
    return [a[1:] for a in page.evaluate("window.__appels") if a[0] == nom]


def test_sans_profil_accueil_et_plus_tard(fenetre):
    p = fenetre(bienvenue={"profil": False})
    p.get_by_text("Dépose ton CV ici").wait_for()
    assert p.evaluate("document.body.classList.contains('sans-profil')")
    p.get_by_role("button", name="Plus tard").click()
    p.wait_for_function("window.__appels.some((a) => a[0] === 'plus_tard')")


def test_reprise_d_un_ancien_dossier(fenetre):
    p = fenetre(
        bienvenue={"profil": False, "reprise": [{"dossier": "D:/Ancien", "date": "01/11/2026"}]},
        reprendre={"ok": False, "erreur": "Copie impossible"},
    )
    p.get_by_text("Bon retour").wait_for()
    p.get_by_role("button", name="Reprendre").click()
    p.get_by_text("Copie impossible").wait_for()
    assert appels(p, "reprendre") == [["D:/Ancien"]]


def test_nouveau_profil_depuis_la_reprise(fenetre):
    p = fenetre(bienvenue={"profil": False, "reprise": [{"dossier": "D:/A", "date": "x"}]})
    p.get_by_role("button", name="Nouveau profil").click()
    p.get_by_text("Dépose ton CV ici").wait_for()


def test_cv_depose_refuse_autre_chose_qu_un_cv(fenetre):
    p = fenetre(bienvenue={"profil": False}, lire_cv={"ok": False, "erreur": "CV illisible"})
    p.get_by_text("Dépose ton CV ici").wait_for()
    p.evaluate("cvDepose('C:/notes.txt')")
    p.get_by_text("Ce n'est pas un CV PDF ou Word").wait_for()
    assert appels(p, "lire_cv") == []
    p.evaluate("cvDepose('C:/cv.pdf')")
    p.get_by_text("CV illisible").wait_for()  # back to the CV screen, with the reason
    assert appels(p, "lire_cv") == [["C:/cv.pdf"]]


def test_avec_profil_l_application_demarre(fenetre):
    p = fenetre(bienvenue={"profil": True})
    p.wait_for_function("window.__appels.some((a) => a[0] === 'annonce_maj')")
    assert not p.evaluate("document.body.classList.contains('sans-profil')")
    assert appels(p, "plus_tard") == []


def test_bienvenue_en_echec_jamais_de_fenetre_vide(fenetre):
    p = fenetre(bienvenue={"rejette": "API absente"})
    p.wait_for_function("window.__appels.some((a) => a[0] === 'annonce_maj')")
    assert p.locator("#vue").inner_text().strip()
