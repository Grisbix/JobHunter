"""`jobhunter migrate`: a 2.x data folder (French names) moves to the 3.0 layout.

A fictitious 2.x installation: a queue whose CV and letter links point into
CV/Par_offre and Lettres/Par_offre, a tracking file with a proof screenshot, backups,
an API key file, the profile, a CV in Mon_CV, templates, follow-up letters — plus what
the first update to 3.0 puts next to it (data/sources_config.json, the 3.0 example
profile). After the migration nothing is lost, every link still opens its file, and
a failure midway puts everything back exactly as it was.
"""

import hashlib
import json
import os
import time
import zipfile
from pathlib import Path

import pytest

from jobhunter import links, root
from jobhunter.programs import migrate as M


def ecrire(r: Path, rel: str, contenu: str | bytes) -> Path:
    p = r / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(contenu, bytes):
        p.write_bytes(contenu)
    else:
        p.write_text(contenu, encoding="utf-8")
    return p


@pytest.fixture
def ancienne(tmp_path):
    r = tmp_path / "JobHunter"
    cv = ecrire(r, "CV/Par_offre/CV_Gabriel_Acme.pdf", b"%PDF cv")
    lt = ecrire(r, "Lettres/Par_offre/Lettre_Gabriel_Acme.pdf", b"%PDF lettre")
    capture = ecrire(r, "Scripts/_preuves/2026-10-19_Acme.png", b"png")
    file_ = [
        {
            "entreprise": "Acme",
            "poste": "Analyste ESG",
            "fit": 9,
            "cv": links.url_de(cv),
            "lettre": links.url_de(lt),
        },
        {"entreprise": "Beta", "poste": "Chargé RSE", "fit": 7},
    ]
    ecrire(r, "Scripts/apply_queue.json", json.dumps(file_))
    ecrire(r, "Scripts/descriptions.json", json.dumps({"Acme|Analyste ESG": "texte"}))
    suivi = {
        "Acme|Analyste ESG": {
            "s": "postulé",
            "d": "2026-10-19",
            "envoi": "confirmé",
            "preuve": {"texte": "Merci", "capture": str(capture)},
        }
    }
    ecrire(r, "Scripts/suivi.json", json.dumps(suivi))
    ecrire(r, "Scripts/_sauvegardes/2026-10-18/apply_queue.json", "[]")
    ecrire(r, "Scripts/adzuna.json", '{"app_id": "x"}')
    ecrire(r, "Scripts/sources_config.json", '{"mien": 1}')
    ecrire(r, "Scripts/_rendement.jsonl", "{}\n")
    ecrire(r, "profil/profil.json", '{"identite": {"nom": "Camille"}}')
    ecrire(r, "profil/profil.json.bak", "{}")
    ecrire(r, "profil/exemple_finance_esg.json", '{"exemple": 1}')
    ecrire(r, "Mon_CV/LISEZ-MOI.txt", "dépose ton CV ici")
    ecrire(r, "Mon_CV/mon_cv.docx", b"docx")
    ecrire(r, "CV/Modèles/CV_esg.docx", b"modele")
    ecrire(r, "CV/Faits.json", "{}")
    ecrire(r, "Lettres/Relances/Relance_J7_Acme.txt", "relance")
    ecrire(r, "Lettres/Messages/Message_Acme.txt", "message")
    ecrire(r, "VERSION", "2.25.0")
    # What the first update to 3.0 adds next to it (shipped files).
    ecrire(r, "data/sources_config.json", '{"livre": 1}')
    ecrire(r, "profile/example_finance_esg.json", '{"exemple": 1}')
    ecrire(r, "My_CV/README.txt", "put your CV here")
    return r


def empreinte(r: Path) -> dict[str, str]:
    """Every file of the folder and its content (the migration backups aside)."""
    return {
        p.relative_to(r).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(r.rglob("*"))
        if p.is_file() and not p.name.startswith("_backup_migration_")
    }


def test_detection(ancienne):
    assert not root.anglais(ancienne)
    assert M.a_migrer(ancienne)
    assert M.automatique(ancienne)  # VERSION: a published installation
    (ancienne / "VERSION").unlink()
    assert not M.automatique(ancienne)  # a development copy, or a pip install


def test_migration_complete(ancienne):
    r = ancienne
    assert M.migrer(r, bavard=False) == 0
    assert root.anglais(r)
    for vieux in ("Scripts", "profil", "Mon_CV", "Lettres"):
        assert not (r / vieux).exists(), vieux
    d = r / "data"
    assert json.loads((d / "applications.json").read_text(encoding="utf-8"))
    assert (d / "descriptions.json").exists() and (d / "adzuna.json").exists()
    assert (d / "_backups" / "2026-10-18" / "apply_queue.json").exists()
    assert (d / "_source_yield.jsonl").exists()
    # your configuration wins; the shipped one is set aside
    assert json.loads((d / "sources_config.json").read_text(encoding="utf-8")) == {"mien": 1}
    assert (d / "sources_config.json.nouveau").exists()
    assert json.loads((r / "profile" / "profile.json").read_text(encoding="utf-8"))
    assert (r / "profile" / "profile.json.bak").exists()
    assert (r / "profile" / "example_finance_esg.json").exists()
    assert (r / "My_CV" / "mon_cv.docx").exists()
    assert (r / "CV" / "Templates" / "CV_esg.docx").exists()
    assert (r / "CV" / "Facts.json").exists()
    assert (r / "Letters" / "Follow_ups" / "Relance_J7_Acme.txt").exists()
    assert (r / "Letters" / "Messages" / "Message_Acme.txt").exists()
    # the links: rewritten, and they open their file
    file_ = json.loads((d / "apply_queue.json").read_text(encoding="utf-8"))
    assert [(o["entreprise"], o["poste"]) for o in file_] == [
        ("Acme", "Analyste ESG"),
        ("Beta", "Chargé RSE"),
    ]
    assert "By_offer" in file_[0]["cv"] and links.existe(file_[0]["cv"])
    assert "Letters/By_offer" in file_[0]["lettre"] and links.existe(file_[0]["lettre"])
    capture = json.loads((d / "applications.json").read_text(encoding="utf-8"))[
        "Acme|Analyste ESG"
    ]["preuve"]["capture"]
    assert Path(capture).exists() and "_proofs" in capture
    # the backup holds what cannot be rebuilt
    (zp,) = r.glob("_backup_migration_*.zip")
    with zipfile.ZipFile(zp) as z:
        noms = set(z.namelist())
    assert {"Scripts/suivi.json", "Scripts/apply_queue.json", "profil/profil.json"} <= noms
    assert not any("Par_offre" in n for n in noms)
    assert not (r / M.ATTENTE).exists()


def test_deuxieme_passage_ne_fait_rien(ancienne):
    assert M.migrer(ancienne, bavard=False) == 0
    avant = empreinte(ancienne)
    assert M.migrer(ancienne, bavard=False) == 0
    assert empreinte(ancienne) == avant


def test_echec_remet_tout_comme_avant(ancienne, monkeypatch):
    avant = empreinte(ancienne)
    vrai = M._atomique.ecrire_json

    def panne(chemin, obj):
        if Path(chemin).name == "applications.json":
            raise OSError("disque plein")
        vrai(chemin, obj)

    monkeypatch.setattr(M._atomique, "ecrire_json", panne)
    assert M.migrer(ancienne, bavard=False) == 1
    assert empreinte(ancienne) == avant
    assert not root.anglais(ancienne)
    assert not (ancienne / "Scripts" / "apply_queue.json.lock").exists()


def test_file_occupee_rien_n_est_touche(ancienne):
    avant = empreinte(ancienne)
    # A live process (this test's parent) holds the queue.
    (ancienne / "Scripts" / "apply_queue.json.lock").write_text(
        f"{os.getppid()} {time.time()}", encoding="utf-8"
    )
    assert M.migrer(ancienne, bavard=False) == M.OCCUPE
    sans_verrou = {k: v for k, v in empreinte(ancienne).items() if not k.endswith(".lock")}
    assert sans_verrou == avant
    assert not list(ancienne.glob("_backup_migration_*.zip"))


def test_dossier_de_documents_ailleurs(ancienne, tmp_path):
    """`chemins.json` puts the per-offer documents outside the root: they move too."""
    ailleurs = tmp_path / "Documents_JobHunter"
    doc = ecrire(ailleurs, "Lettres/Par_offre/L.pdf", b"%PDF")
    ecrire(ancienne, "Scripts/chemins.json", json.dumps({"documents": str(ailleurs)}))
    file_ = json.loads((ancienne / "Scripts" / "apply_queue.json").read_text(encoding="utf-8"))
    file_[1]["lettre"] = links.url_de(doc)
    ecrire(ancienne, "Scripts/apply_queue.json", json.dumps(file_))
    assert M.migrer(ancienne, bavard=False) == 0
    assert (ailleurs / "Letters" / "By_offer" / "L.pdf").exists()
    assert (ancienne / "data" / "paths.json").exists()
    apres = json.loads((ancienne / "data" / "apply_queue.json").read_text(encoding="utf-8"))
    assert links.existe(apres[1]["lettre"])


def test_traduire_garde_le_reste_du_chemin(tmp_path):
    r = tmp_path
    paires = M.prefixes(r, None)
    assert (
        M.traduire(r / "CV" / "Par_offre" / "a b.pdf", paires) == r / "CV" / "By_offer" / "a b.pdf"
    )
    assert M.traduire(r / "Scripts", paires) == r / "data"
    assert M.traduire(tmp_path.parent / "ailleurs.pdf", paires) == tmp_path.parent / "ailleurs.pdf"


@pytest.fixture
def lettres_tenu(monkeypatch):
    """`Lettres/` held open by another program: neither renamed nor removed (21/10/2026)."""
    vrai_rename, vrai_rmdir = M.os.rename, Path.rmdir

    def rename(a, b):
        if Path(a).name == "Lettres":
            raise PermissionError(5, "Accès refusé")
        vrai_rename(a, b)

    def rmdir(self):
        if self.name == "Lettres":
            raise PermissionError(5, "Accès refusé")
        vrai_rmdir(self)

    monkeypatch.setattr(M.os, "rename", rename)
    monkeypatch.setattr(Path, "rmdir", rmdir)


def test_dossier_tenu_ouvert_son_contenu_part(ancienne, lettres_tenu, capsys):
    r = ancienne
    assert M.migrer(r) == 0
    assert root.anglais(r)
    assert (r / "Letters" / "Follow_ups" / "Relance_J7_Acme.txt").exists()
    assert (r / "Letters" / "Messages" / "Message_Acme.txt").exists()
    assert list((r / "Lettres").iterdir()) == []  # left in place, empty
    assert "Lettres/ est resté, vide" in capsys.readouterr().out
    file_ = json.loads((r / "data" / "apply_queue.json").read_text(encoding="utf-8"))
    assert links.existe(file_[0]["lettre"])


def test_dossier_tenu_ouvert_puis_echec_tout_revient(ancienne, lettres_tenu, monkeypatch):
    avant = empreinte(ancienne)
    vrai = M._atomique.ecrire_json

    def panne(chemin, obj):
        if Path(chemin).name == "applications.json":
            raise OSError("disque plein")
        vrai(chemin, obj)

    monkeypatch.setattr(M._atomique, "ecrire_json", panne)
    assert M.migrer(ancienne, bavard=False) == 1
    assert empreinte(ancienne) == avant
    assert not (ancienne / "Letters").exists()
