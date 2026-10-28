"""3.61: the daily backups compressed (416 MB for seven days became ~110), the dead
dependencies gone (openpyxl unused, requests replaced by httpx)."""

import gzip
import json
import tomllib
from pathlib import Path

from jobhunter.storage import backups

RACINE = Path(__file__).resolve().parent.parent


def test_ecrire_compresse_et_relit(tmp_path):
    src = tmp_path / "apply_queue.json"
    src.write_text(json.dumps([{"poste": "Analyste ESG"}] * 500), encoding="utf-8")
    d = tmp_path / "2026-10-28"
    d.mkdir()
    gz = backups.ecrire(src, d)
    assert gz.name == "apply_queue.json.gz" and gz.stat().st_size < src.stat().st_size / 5
    assert backups.fichier(d, "apply_queue.json") == gz
    assert backups.lire_texte(gz) == src.read_text(encoding="utf-8")
    assert not list(d.glob("*.tmp"))


def test_une_sauvegarde_d_avant_3_61_se_lit_encore(tmp_path):
    (tmp_path / "apply_queue.json").write_text("[]", encoding="utf-8")
    f = backups.fichier(tmp_path, "apply_queue.json")
    assert f == tmp_path / "apply_queue.json" and backups.lire_texte(f) == "[]"
    assert backups.fichier(tmp_path, "descriptions.json") is None


def test_compresser_garde_le_contenu(tmp_path):
    for nom, texte in (("apply_queue.json", "[1, 2]"), ("descriptions.json", "{}")):
        (tmp_path / nom).write_text(texte, encoding="utf-8")
    (tmp_path / "notes.txt").write_text("à garder")
    assert backups.compresser(tmp_path) == 2
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "apply_queue.json.gz",
        "descriptions.json.gz",
        "notes.txt",
    ]
    assert gzip.decompress((tmp_path / "apply_queue.json.gz").read_bytes()) == b"[1, 2]"


def test_en_clair_donne_un_chemin_lisible(tmp_path):
    src = tmp_path / "apply_queue.json"
    src.write_text("[]", encoding="utf-8")
    gz = backups.ecrire(src, tmp_path / ".")
    with backups.en_clair(gz) as clair:
        assert clair.name == "apply_queue.json" and clair.read_text(encoding="utf-8") == "[]"
    assert not clair.exists()


def test_le_pipeline_compresse_aussi_les_anciennes(tmp_path, monkeypatch):
    from jobhunter.programs import daily_pipeline as pq

    monkeypatch.setattr(pq, "SCRIPTS", tmp_path)
    (tmp_path / "apply_queue.json").write_text("[]", encoding="utf-8")
    vieux = tmp_path / "_backups" / "2026-10-20"
    vieux.mkdir(parents=True)
    (vieux / "apply_queue.json").write_text("[0]", encoding="utf-8")
    cible = pq.sauvegarder()
    assert (cible / "apply_queue.json.gz").is_file()
    assert [p.name for p in vieux.iterdir()] == ["apply_queue.json.gz"]


def test_restore_lit_les_sauvegardes_compressees(tmp_path, monkeypatch):
    from jobhunter.programs import restore

    d = tmp_path / "_backups" / "2026-10-28"
    d.mkdir(parents=True)
    src = tmp_path / "apply_queue.json"
    src.write_text("[]", encoding="utf-8")
    backups.ecrire(src, d)
    monkeypatch.setattr(restore, "_dossier", lambda: tmp_path)
    s = [x for x in restore.sauvegardes() if x.nom == "2026-10-28"]
    assert s and restore._lire(s[0].file) == []


def test_plus_d_openpyxl_ni_de_requests():
    deps = tomllib.loads((RACINE / "pyproject.toml").read_text(encoding="utf-8"))
    noms = " ".join(deps["project"]["dependencies"])
    assert "openpyxl" not in noms and "requests" not in noms
    exigences = (RACINE / "requirements.txt").read_text(encoding="utf-8")
    assert "openpyxl" not in exigences and "requests" not in exigences
    for f in (RACINE / "src").rglob("*.py"):
        texte = f.read_text(encoding="utf-8")
        assert "import requests" not in texte and "import openpyxl" not in texte, f
