"""The guided application in the web window (web/guided.py), with a stand-in program."""

import json
import sys
import time

from jobhunter import guided_apply
from jobhunter.web import guided

# Stands in for apply_runner --pilote: one offer, ready, waits, then the user's answer.
PROGRAMME = r"""
import json, sys
def ev(**k):
    print("@JH " + json.dumps(k, ensure_ascii=False), flush=True)
print("Chrome ouvert", flush=True)
ev(type="offre", i=1, total=1, entreprise="Acme", poste="Analyste ESG")
ev(type="pret", couverture=90, bouton="Postuler")
ev(type="attente")
cmd = sys.stdin.readline().strip()
if cmd == "quitter":
    sys.exit(0)
ev(type="resultat", etat="confirmé" if cmd == "envoye" else "sauté", texte="Merci")
ev(type="fin")
ev(type="attente")
sys.stdin.readline()
"""


def _attendre(cond, delai=10.0):
    fin = time.time() + delai
    while time.time() < fin:
        if cond():
            return True
        time.sleep(0.05)
    return False


class _Api(guided.CandidatureApi):
    def __init__(self, offres):
        self.offres = offres

    def _file(self):
        return self.offres


def test_une_offre_de_bout_en_bout():
    api = _Api([])
    api._seance = guided.Seance(1, [sys.executable, "-c", PROGRAMME], ".")
    s = api._seance
    assert _attendre(lambda: s.attente)
    e = api.candidature_etat()
    assert e["zones"]["offre"]["texte"] == "1/1 · Acme — Analyste ESG"
    assert "« Postuler »" in e["zones"]["etat"]["texte"] and e["zones"]["etat"]["ton"] == "acc"
    assert e["journal"] == ["Chrome ouvert"]
    assert api.candidature_commande("cliquer")["ok"] is False  # unknown: never passed on
    assert api.candidature_commande("envoye") == {"ok": True}
    assert api.candidature_commande("envoye")["ok"] is False  # the program works: wait
    assert _attendre(lambda: s.attente)
    e = api.candidature_etat()
    assert e["envois"] == 1 and e["zones"]["resultat"]["ton"] == "ok"
    assert api.candidature_arreter() is True
    assert _attendre(lambda: s.code is not None)
    assert api.candidature_etat()["fini"] is True


def test_rien_de_coche():
    r = _Api([{"entreprise": "Acme", "poste": "P"}]).candidature_guidee(["Autre|X"])
    assert r == {"ok": False, "erreur": "Coche d'abord des offres."}


def test_la_selection_ecrite_pour_le_programme(monkeypatch, tmp_path):
    lances = []

    class Faux:
        code = None

        def __init__(self, n, cmd, cwd):
            lances.append((n, cmd, cwd))

    monkeypatch.setattr(guided, "Seance", Faux)
    monkeypatch.setattr("jobhunter.root.scripts", lambda: tmp_path)
    api = _Api(
        [
            {"entreprise": "Acme", "poste": "Analyste", "url": "https://x"},
            {"entreprise": "Beta", "poste": "Chargée RSE"},
        ]
    )
    assert api.candidature_guidee(["Beta|Chargée RSE"]) == {"ok": True, "n": 1}
    sel = json.loads((tmp_path / "apply_selection.json").read_text(encoding="utf-8"))
    assert sel == [{"entreprise": "Beta", "poste": "Chargée RSE"}]
    n, cmd, cwd = lances[0]
    assert cmd[1:] == [
        "-m",
        "jobhunter.programs.apply_runner",
        "--selection",
        str(tmp_path / "apply_selection.json"),
        "--pilote",
    ]
    # one run at a time
    assert api.candidature_guidee(["Beta|Chargée RSE"])["ok"] is False


def test_aucune_commande_n_envoie():
    # The page can only pass on these; none of them is a click on Send.
    assert set(guided_apply.COMMANDES) == {"envoye", "saute", "reremplir", "rouvrir"}


def test_fermer_la_fenetre_arrete_la_seance():
    api = _Api([])
    api._seance = guided.Seance(1, [sys.executable, "-c", PROGRAMME], ".")
    assert _attendre(lambda: api._seance.attente)
    api._fermer_seance()
    assert api._seance.proc.poll() is not None
