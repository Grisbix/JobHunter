"""3.88, audit of 2026-11-15: the Store package inside the author's signature, Edge when
Chrome is missing, the logos at every size, the Store's origin asked once."""

import hashlib
import importlib.util
import json

import pytest
from conftest import RACINE
from test_update import V13, zip_de

from jobhunter import frozen
from jobhunter import signature as sig
from jobhunter.navigation import browser
from jobhunter.programs import update as maj

SECRET = bytes(range(32))


def _outil(nom: str, chemin: str):
    spec = importlib.util.spec_from_file_location(nom, RACINE / chemin)
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ── The MSIX in the signed manifest ──────────────────────────────────────────


def test_manifeste_sans_paquet_inchange():
    m = sig.manifeste("1.0.0", {"a": b"x"}, b"setup")
    assert set(m) == {"version", "fichiers", "setup"}  # what older releases signed
    assert sig.controler_msix(m, b"n'importe quoi") is False


def test_paquet_signe_reconnu_autre_refuse():
    m = sig.manifeste("1.0.0", {}, b"setup", b"paquet")
    assert m["msix"] == hashlib.sha256(b"paquet").hexdigest()
    assert sig.controler_msix(m, b"paquet") is True
    with pytest.raises(sig.SignatureInvalide):
        sig.controler_msix(m, b"paquet remplace")


@pytest.fixture
def release(tmp_path, monkeypatch):
    """A signed release's files on disk: (check_msix, msix path, signature path)."""
    monkeypatch.setattr(sig, "CLE_PUBLIQUE", sig.publique(SECRET).hex())
    msix = tmp_path / "JobHunter.msix"
    msix.write_bytes(b"paquet")
    signature = tmp_path / "signature.json"
    signature.write_bytes(sig.emballer(SECRET, sig.manifeste("3.88.0", {}, b"s", b"paquet")))
    return _outil("outil_check_msix", "tools/installer/check_msix.py"), msix, signature


def test_check_msix_accepte_le_paquet_signe(release):
    outil, msix, signature = release
    assert outil.controler("3.88.0", msix, signature)[0] == 0
    assert outil.main(["v3.88.0", str(msix), str(signature)]) == 0  # the tag, as store.yml gives it


def test_check_msix_refuse_un_paquet_remplace(release):
    outil, msix, signature = release
    msix.write_bytes(b"paquet d'un autre")
    code, phrase = outil.controler("3.88.0", msix, signature)
    assert code == 1 and "diffère" in phrase


def test_check_msix_refuse_une_autre_version_ou_une_signature_fausse(release):
    outil, msix, signature = release
    assert outil.controler("3.89.0", msix, signature)[0] == 1  # an old signature replayed
    doc = json.loads(signature.read_bytes())
    doc["manifeste"]["msix"] = hashlib.sha256(b"autre").hexdigest()
    signature.write_text(json.dumps(doc), encoding="utf-8")
    assert outil.controler("3.88.0", msix, signature)[0] == 1
    signature.unlink()
    assert outil.controler("3.88.0", msix, signature)[0] == 1


def test_check_msix_signature_d_avant_la_388_dite(release):
    outil, msix, signature = release
    signature.write_bytes(sig.emballer(SECRET, sig.manifeste("3.88.0", {}, b"s")))
    code, phrase = outil.controler("3.88.0", msix, signature)
    assert code == 0 and phrase.startswith("::warning::")


# ── The signing tool ─────────────────────────────────────────────────────────


@pytest.fixture
def signature_outil(tmp_path, monkeypatch):
    m = _outil("outil_signature_388", "tools/signature.py")
    cle = tmp_path / "prive" / "cle_signature"
    cle.parent.mkdir()
    cle.write_text(SECRET.hex() + "\n", encoding="ascii")
    monkeypatch.setattr(m, "CLE_PRIVEE", cle)
    monkeypatch.setattr(m, "RACINE", tmp_path)
    monkeypatch.setattr(sig, "CLE_PUBLIQUE", sig.publique(SECRET).hex())
    exe = b"MZ 1.3.0"
    urls = {
        maj.TAG_URL.format("1.3.0"): zip_de(V13, "JobHunter-1.3.0"),
        maj.ASSET_URL.format("1.3.0", maj.SETUP): exe,
        maj.ASSET_URL.format("1.3.0", maj.SETUP + ".sha256"): hashlib.sha256(exe)
        .hexdigest()
        .encode(),
    }
    monkeypatch.setattr(m, "_get", lambda url: urls[url])
    appels: list[tuple[str, ...]] = []

    class Reponse:
        returncode = 0
        stdout = '{"isPrerelease": false}'

    def gh(*args, check=True):
        appels.append(args)
        return Reponse()

    monkeypatch.setattr(m, "_gh", gh)
    return m, appels, Reponse


def _manifeste(tmp_path):
    return sig.ouvrir((tmp_path / "dist" / sig.FICHIER).read_bytes(), "1.3.0")


def test_signer_couvre_le_paquet_du_store(signature_outil, tmp_path, monkeypatch):
    outil, appels, _ = signature_outil
    monkeypatch.setattr(outil, "_msix", lambda version: b"paquet 1.3.0")
    assert outil.signer("1.3.0", publier=False) == 0
    assert sig.controler_msix(_manifeste(tmp_path), b"paquet 1.3.0") is True
    assert appels == []  # nothing published, nothing sent


def test_signer_sans_paquet_ne_lance_pas_le_store(signature_outil, tmp_path, monkeypatch):
    outil, appels, _ = signature_outil
    monkeypatch.setattr(outil, "_msix", lambda version: None)
    assert outil.signer("1.3.0", publier=True) == 0
    assert "msix" not in _manifeste(tmp_path)
    assert not any("store.yml" in a for a in appels)


def test_publier_une_release_signee_lance_l_envoi_au_store(signature_outil, monkeypatch):
    outil, appels, _ = signature_outil
    monkeypatch.setattr(outil, "_msix", lambda version: b"paquet")
    assert outil.signer("1.3.0", publier=True) == 0
    envoi = [a for a in appels if "store.yml" in a]
    assert len(envoi) == 1 and "tag=v1.3.0" in envoi[0]


def test_une_version_de_test_ne_part_pas_au_store(signature_outil, monkeypatch):
    outil, appels, reponse = signature_outil
    monkeypatch.setattr(reponse, "stdout", '{"isPrerelease": true}')
    monkeypatch.setattr(outil, "_msix", lambda version: b"paquet")
    assert outil.signer("1.3.0", publier=True) == 0
    assert not any("store.yml" in a for a in appels)
    monkeypatch.setattr(reponse, "stdout", "")  # gh did not answer: not sent either
    assert outil._version_de_test("1.3.0") is True


def test_release_sans_msix_404(signature_outil, monkeypatch):
    import urllib.error

    outil, _, _ = signature_outil

    def get(url):
        raise urllib.error.HTTPError(url, 404, "Not Found", None, None)  # type: ignore[arg-type]

    monkeypatch.setattr(outil, "_get", get)
    assert outil._msix("1.3.0") is None


def test_store_yml_controle_avant_d_envoyer():
    texte = (RACINE / ".github/workflows/store.yml").read_text(encoding="utf-8")
    assert texte.index("check_msix.py") < texte.index("msstore publish")
    assert "workflow_dispatch" in texte  # what `signer --publier` runs


# ── Who installed the package: asked once ────────────────────────────────────


def test_origine_du_paquet_demandee_une_fois(monkeypatch):
    appels = []

    def kind(famille):
        appels.append(famille)
        return "Store"

    monkeypatch.setattr(frozen, "_DU_STORE", {})
    monkeypatch.setattr(frozen, "famille_msix", lambda: "Grisbix.JobHunter_abc")
    monkeypatch.setattr(frozen, "_signature_du_paquet", kind)
    assert frozen.msix_du_store() is True and frozen.msix_du_store() is True
    assert appels == ["Grisbix.JobHunter_abc"]


def test_origine_sans_reponse_redemandee(monkeypatch):
    reponses = [None, "Developer"]
    monkeypatch.setattr(frozen, "_DU_STORE", {})
    monkeypatch.setattr(frozen, "famille_msix", lambda: "Grisbix.JobHunter_abc")
    monkeypatch.setattr(frozen, "_signature_du_paquet", lambda f: reponses.pop(0))
    assert frozen.msix_du_store() is False  # PowerShell silent: not remembered
    assert frozen.msix_du_store() is False  # installed from the release's file
    assert reponses == []


# ── Edge when Chrome is missing ──────────────────────────────────────────────


class _Chromium:
    def __init__(self, erreurs):
        self.erreurs, self.canaux = erreurs, []

    def launch_persistent_context(self, channel, **options):
        self.canaux.append(channel)
        if channel in self.erreurs:
            raise RuntimeError(self.erreurs[channel])
        return (channel, options)


ABSENT = "Chromium distribution 'chrome' is not found. Run \"npx playwright install chrome\""


def test_edge_quand_chrome_manque():
    c = _Chromium({"chrome": ABSENT})
    assert browser.contexte_persistant(c, user_data_dir="p", headless=True) == (
        "msedge",
        {"user_data_dir": "p", "headless": True},
    )
    assert c.canaux == ["chrome", "msedge"]


def test_chrome_present_edge_jamais_essaye():
    c = _Chromium({})
    assert browser.contexte_persistant(c, user_data_dir="p")[0] == "chrome"
    assert c.canaux == ["chrome"]


def test_autre_panne_de_chrome_dite_telle_quelle():
    c = _Chromium({"chrome": "TimeoutError: profil verrouillé"})
    with pytest.raises(RuntimeError, match="verrouillé"):
        browser.contexte_persistant(c, user_data_dir="p")
    assert c.canaux == ["chrome"]  # a locked profile is not a missing browser
    c = _Chromium({"chrome": ABSENT, "msedge": ABSENT.replace("chrome", "msedge")})
    with pytest.raises(RuntimeError, match="msedge"):
        browser.contexte_persistant(c, user_data_dir="p")


def test_plus_aucun_profil_dedie_n_impose_chrome():
    for nom in ("access", "apply_runner", "test_site_access"):
        texte = (RACINE / "src/jobhunter/programs" / f"{nom}.py").read_text(encoding="utf-8")
        assert 'channel="chrome"' not in texte, nom
        assert "contexte_persistant(" in texte, nom


# ── The package's logos ──────────────────────────────────────────────────────


def test_logos_a_toutes_les_tailles():
    msix = _outil("outil_msix_388", "tools/installer/msix.py")
    noms = msix.noms_des_variantes()
    assert noms["Square44x44Logo.scale-200.png"] == 88
    assert noms["Square150x150Logo.scale-100.png"] == 150
    assert noms["StoreLogo.scale-400.png"] == 200
    assert noms["Square44x44Logo.targetsize-24_altform-unplated.png"] == 24
    assert len(noms) == 3 * len(msix.ECHELLES) + len(msix.CIBLES)


def test_sans_makepri_les_trois_logos_restent(tmp_path, monkeypatch):
    msix = _outil("outil_msix_388b", "tools/installer/msix.py")
    monkeypatch.setattr(msix, "makepri", lambda: None)
    monkeypatch.setattr(msix, "DIST", tmp_path / "dist")
    disposition = tmp_path / "msix"
    msix.logos(disposition / "Assets")
    assert msix.variantes(disposition) is False
    assert sorted(p.name for p in (disposition / "Assets").iterdir()) == sorted(msix.LOGOS)
    assert not (disposition / "resources.pri").exists()
