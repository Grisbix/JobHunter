"""3.68: the Store package gets a desktop icon at its first start, once; the compiled
application knows its version (it showed « ? » and called every release new)."""

from pathlib import Path

from jobhunter import frozen, root
from jobhunter.programs import shortcut
from jobhunter.programs import update as mise_a_jour
from jobhunter.web import api


def _store(monkeypatch, tmp_path):
    donnees = tmp_path / "data"
    donnees.mkdir()
    bureau = tmp_path / "Bureau"
    bureau.mkdir()
    faits = []
    monkeypatch.setattr(frozen, "famille_msix", lambda: "Grisbix.JobHunter_abc123")
    monkeypatch.setattr(root, "scripts", lambda: donnees)
    monkeypatch.setattr(shortcut, "dossier_bureau", lambda: bureau)

    def creer(lien, exe, args, dossier, icone, aumid):
        faits.append((exe.name, args, aumid, icone))
        Path(lien).write_bytes(b"lnk")

    monkeypatch.setattr(shortcut, "creer", creer)
    return donnees, bureau, faits


def test_icone_du_bureau_une_seule_fois(monkeypatch, tmp_path):
    donnees, bureau, faits = _store(monkeypatch, tmp_path)
    assert shortcut.bureau_msix()
    assert (bureau / "JobHunter.lnk").is_file()
    exe, args, aumid, icone = faits[0]
    assert exe == "explorer.exe"
    assert args == "shell:AppsFolder\\Grisbix.JobHunter_abc123!JobHunter"
    assert aumid == "Grisbix.JobHunter_abc123!JobHunter"
    # outside the package folder, whose name changes at each update
    assert icone == donnees / "jobhunter.ico" and icone.is_file()
    # deleted by the user: it stays deleted
    (bureau / "JobHunter.lnk").unlink()
    assert not shortcut.bureau_msix()
    assert len(faits) == 1


def test_icone_deja_la_pas_reecrite(monkeypatch, tmp_path):
    donnees, bureau, faits = _store(monkeypatch, tmp_path)
    (bureau / "JobHunter.lnk").write_bytes(b"autre")
    assert shortcut.bureau_msix()
    assert not faits and (bureau / "JobHunter.lnk").read_bytes() == b"autre"


def test_hors_paquet_rien(monkeypatch, tmp_path):
    _donnees, _bureau, faits = _store(monkeypatch, tmp_path)
    monkeypatch.setattr(frozen, "famille_msix", lambda: "")
    assert not shortcut.bureau_msix()
    assert not faits


def test_version_de_l_app_compilee(monkeypatch):
    monkeypatch.setattr(frozen, "est_gele", lambda: True)
    monkeypatch.setattr(mise_a_jour, "version_locale", lambda: "3.66.0")
    assert api._version_installee() == "3.66.0"
    monkeypatch.setattr(mise_a_jour, "version_locale", lambda: "0")
    assert api._version_installee() == "?"


def test_version_inconnue_jamais_nouvelle(monkeypatch):
    monkeypatch.setattr(api, "_version_installee", lambda: "?")
    monkeypatch.setattr(api, "_derniere_version", lambda: "3.68.0")
    monkeypatch.setattr(frozen, "paquet_msix", lambda: False)
    v = api.Api.mise_a_jour(None)  # type: ignore[arg-type]
    assert not v["nouvelle"] and not v["signee"]


def test_le_store_installe_ses_mises_a_jour(monkeypatch):
    monkeypatch.setattr(api, "_version_installee", lambda: "3.66.0")
    monkeypatch.setattr(api, "_derniere_version", lambda: "3.68.0")
    monkeypatch.setattr(frozen, "paquet_msix", lambda: True)
    monkeypatch.setattr(frozen, "msix_du_store", lambda: True)
    monkeypatch.setattr(api, "_signee", lambda v: True)
    v = api.Api.mise_a_jour(None)  # type: ignore[arg-type]
    assert v["store"] and v["nouvelle"]
    assert not v["signee"]  # no « Mettre à jour » button: the Store does it
