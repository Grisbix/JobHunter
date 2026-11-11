"""3.72: faster descriptions, one activity panel, one place per button.

Descriptions written in batches without holding the queue for the whole run, failed
pages rested for two weeks; CV and letter of one offer by its identity; the home
screen's « À faire » made of offers ready to apply to; no button twice.
"""

import datetime
import json
from datetime import date
from pathlib import Path

import js_app

from jobhunter.programs import scrape_desc
from jobhunter.web import api
from jobhunter.web.api import tableau

RACINE = Path(__file__).resolve().parent.parent
STATIQUE = RACINE / "src" / "jobhunter" / "web" / "static"
JS = js_app.source()
HTML = (STATIQUE / "index.html").read_text(encoding="utf-8")
CSS = (STATIQUE / "style.css").read_text(encoding="utf-8")


# --- descriptions ------------------------------------------------------------------------


def _file(tmp_path, offres):
    q = tmp_path / "apply_queue.json"
    q.write_text(json.dumps(offres), encoding="utf-8")
    return q


def test_ecrire_lot_une_seule_transaction(tmp_path):
    q = _file(
        tmp_path,
        [
            {"entreprise": "A", "poste": "a"},
            {"entreprise": "B", "poste": "b", "description": "déjà là"},
            {"entreprise": "C", "poste": "c", "desc_essai": "2026-01-01"},
        ],
    )
    n = scrape_desc.ecrire_lot({"A|a": "texte A", "B|b": "autre", "C|c": "texte C"}, set(), q)
    rows = {f"{x['entreprise']}|{x['poste']}": x for x in json.loads(q.read_text("utf-8"))}
    assert n == 2
    assert rows["B|b"]["description"] == "déjà là"  # written meanwhile: kept
    assert "desc_essai" not in rows["C|c"]


def test_un_echec_est_date(tmp_path):
    q = _file(tmp_path, [{"entreprise": "A", "poste": "a"}])
    assert scrape_desc.ecrire_lot({}, {"A|a"}, q) == 0
    assert json.loads(q.read_text("utf-8"))[0]["desc_essai"] == datetime.date.today().isoformat()


def test_un_echec_recent_attend():
    jour = date(2026, 11, 2)
    assert scrape_desc._recent({"desc_essai": "2026-10-30"}, jour)
    assert not scrape_desc._recent({"desc_essai": "2026-10-01"}, jour)
    assert not scrape_desc._recent({}, jour)
    assert not scrape_desc._recent({"desc_essai": "n'importe"}, jour)


def test_les_liens_rapides_d_abord():
    assert scrape_desc.fetch_api_possible("https://acme.wd3.myworkdayjobs.com/fr/job/Paris/X_1")
    assert not scrape_desc.fetch_api_possible("https://www.linkedin.com/jobs/view/1")
    assert not scrape_desc.fetch_api_possible("")


# --- one offer's CV and letter -------------------------------------------------------------


def test_documents_par_identite(monkeypatch):
    lances = []

    class Faux:
        def __init__(self, cle, libelle, cmd, cwd):
            lances.append(cmd)
            self.code = None

    monkeypatch.setattr(api, "Tache", Faux)
    monkeypatch.setattr("jobhunter.root.scripts", lambda: Path("."))
    a = api.Api()
    a._file = lambda: [{"entreprise": "A", "poste": "a"}]
    assert a.lancer("documents", "A|a")["ok"]
    assert lances[-1][-2:] == ["--oid", "A|a"]


def test_generate_docs_oid_introuvable(monkeypatch, tmp_path, capsys):
    from jobhunter.programs import generate_docs

    q = _file(tmp_path, [{"entreprise": "A", "poste": "a"}])
    monkeypatch.setattr(generate_docs, "QUEUE", q)
    monkeypatch.setattr("sys.argv", ["generate_docs", "--oid", "Z|z", "--dry"])
    assert generate_docs.main() == 1
    assert "introuvable" in capsys.readouterr().out


def test_generate_docs_oid_meme_contrat_masque(monkeypatch, tmp_path, capsys):
    from jobhunter.programs import generate_docs

    q = _file(tmp_path, [{"entreprise": "A", "poste": "Stage a", "contrat": "Stage"}])
    monkeypatch.setattr(generate_docs, "QUEUE", q)
    monkeypatch.setattr("jobhunter.sources.contrats_exclus", lambda: {"Stage"})
    monkeypatch.setattr("sys.argv", ["generate_docs", "--oid", "A|Stage a", "--dry"])
    generate_docs.main()
    assert capsys.readouterr().out.startswith("1 offre(s)")


# --- home screen -----------------------------------------------------------------------------


def test_a_faire_les_offres_pretes():
    offres = [
        {
            "entreprise": "A",
            "poste": "a",
            "fit": 9,
            "statut": "Scan 2026-10-30",
            "cv": "x",
            "lettre": "y",
        },
        {"entreprise": "B", "poste": "b", "fit": 8, "statut": "Scan 2026-10-30"},
        {
            "entreprise": "C",
            "poste": "c",
            "fit": 10,
            "statut": "Scan 2026-10-30",
            "cv": "x",
            "lettre": "y",
        },
    ]
    d = tableau(offres, {"C|c": {"s": "postulé", "d": "2026-10-31"}}, date(2026, 11, 2))
    assert [o["entreprise"] for o in d["a_postuler"]] == ["A"]


def test_fenetre_dit_le_plein_ecran():
    a = api.Api()
    assert a.fenetre("etat") is None  # no window: nothing to say
    a._fenetre = object()
    a._plein = lambda: True
    assert a.fenetre("etat") is True


# --- interface -------------------------------------------------------------------------------


def test_pas_de_toast_a_chaque_lot():
    assert 'm.texte.startsWith("!")) toast(m.texte, true)' in JS
    assert "function dessinerActivite()" in JS and "jauge(pct)" in JS


def test_panneau_clair_sans_console():
    debut = CSS.index(".tache {")
    bloc = CSS[debut : CSS.index("}", debut)]
    assert "var(--sombre)" not in bloc and "var(--verre-fort)" in bloc
    assert "Cascadia Mono" not in CSS[debut : debut + 3000]


def test_chaque_bouton_a_une_place():
    assert 'bouton("Annuler", "fleche", annulerGeste)' not in JS
    assert JS.count('"disponibilite")') == 1  # Offres only
    assert JS.count('"Vérifier les mises à jour"') <= 1  # Maintenance only
    assert 'carte("Profils"' not in JS
    assert 'bouton("Nouveau profil…", "profil", nouveauProfil, "plein")' not in JS
    assert 'data-ecran="relances"' not in HTML
    assert 'aller("relances")' in JS  # one click from Candidatures


def test_aucun_github_visible():
    for texte in (JS, HTML):
        visibles = [
            ligne for ligne in texte.splitlines() if "GitHub" in ligne and "//" not in ligne
        ]
        assert not visibles, visibles


def test_barre_blanche():
    assert ".vue.plein .colonne > .remplit" in CSS


def test_icone_plein_ecran():
    assert "function iconePlein(plein)" in JS
    assert 'fenetre("etat").then(iconePlein)' in JS
