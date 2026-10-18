"""La mise a jour ne doit jamais perdre ce que l'utilisateur a fait (mise_a_jour).

Hors reseau : les ZIP « GitHub » sont fabriques en memoire et servis a la place du
telechargement, l'installation vit dans un dossier temporaire. Un fichier modifie
n'est pas ecrase, meme a la premiere mise a jour (trou de la 1.2.0, mesure sur une
vraie installation) ; un fichier retire part s'il est intact ; les donnees ne sont
jamais ecrites ; un controle rate remet la version d'avant, comme --annuler.
Converti depuis Scripts/test_mise_a_jour.py.
"""

import argparse
import io
import json
import sys
import zipfile
from pathlib import Path

import pytest

from jobhunter.programmes import mise_a_jour as maj


def zip_de(fichiers, racine="JobHunter-main"):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(racine + "/", "")
        for rel, txt in fichiers.items():
            z.writestr(f"{racine}/{rel}", txt)
    return buf.getvalue()


CHANGELOG = """# Nouveautés

## 1.3.0 — 2026-10-15
- bouton de mise à jour

## 1.2.0 — 2026-10-01
- plafond de langue

## 1.1.0 — 2026-09-01
- ancienne
"""

V12 = {
    "VERSION": "1.2.0\n",
    "Scripts/a.py": "A = 1\n",
    "Scripts/b.py": "B = 1\n",
    "Scripts/vieux.py": "V = 1\n",
    "Scripts/vieux_modifie.py": "W = 1\n",
    "Scripts/sources_config.json": "{}\n",
    "Mon_CV/LISEZ-MOI.txt": "mets ton CV ici\n",
    "Scripts/stable.py": "S = 1\n",
}
V13 = {
    "VERSION": "1.3.0\n",
    "Scripts/a.py": "A = 2\n",
    "Scripts/b.py": "B = 2\n",
    "Scripts/nouveau.py": "N = 1\n",
    "Scripts/sources_config.json": '{"v": 2}\n',
    "Mon_CV/LISEZ-MOI.txt": "autre texte\n",
    "CHANGELOG.md": CHANGELOG,
    "profil/profil.json": '{"pirate": 1}\n',
    "Scripts/stable.py": "S = 1\n",
}
ZIPS = {maj.ZIP_URL: zip_de(V13), maj.TAG_URL.format("1.2.0"): zip_de(V12, "JobHunter-1.2.0")}


def ecrire(d, rel, txt):
    (d / rel).parent.mkdir(parents=True, exist_ok=True)
    (d / rel).write_text(txt, encoding="utf-8", newline="")


def lire(d, rel):
    p = d / rel
    return p.read_text(encoding="utf-8") if p.exists() else None


@pytest.fixture
def installer(tmp_path, monkeypatch):
    """installer(fichiers, zips, controle) -> dossier ; mise_a_jour pointe dessus."""

    def faire(fichiers=V12, zips=ZIPS, controle=True):
        for rel, txt in fichiers.items():
            ecrire(tmp_path, rel, txt)
        monkeypatch.setattr(maj, "RACINE", tmp_path)
        monkeypatch.setattr(maj, "MANIFESTE", tmp_path / ".maj_manifeste.json")
        monkeypatch.setattr(maj, "SAUVEGARDES", tmp_path / "_sauvegarde_maj")
        monkeypatch.setattr(maj, "GIT_AVANT", tmp_path / ".maj_git_avant")
        monkeypatch.setattr(maj, "apres", lambda changes_requirements: 0)  # ni pip ni profil

        def _get(url, timeout):
            if url not in zips:
                raise OSError(f"404 {url}")
            return zips[url]

        monkeypatch.setattr(maj, "_get", _get)
        monkeypatch.setattr(maj, "controler", lambda: controle)
        monkeypatch.setattr(maj, "controler_nouveau", lambda: controle)
        return tmp_path

    return faire


def lancer(capsys, verifier=False, forcer=False):
    rc = maj.par_zip(argparse.Namespace(verifier=verifier, forcer=forcer, annuler=False))
    return rc, capsys.readouterr().out


# ── nouveautes, reglages, protection : fonctions pures ─────────────────────────
@pytest.mark.parametrize(
    ("depuis", "jusqua", "present", "absent"),
    [
        ("1.2.0", None, ["1.3.0", "bouton"], []),
        ("1.2.0", None, [], ["plafond"]),
        ("1.1.0", None, ["bouton", "plafond"], []),
        ("1.1.0", "1.2.0", [], ["bouton"]),
        ("0", None, [], ["# Nouveautés"]),  # le titre du fichier n'est jamais repris
    ],
    ids=[
        "voit la suivante",
        "ne revoit pas la sienne",
        "voit les deux",
        "jusqu'a exclut la suite",
        "sans le titre",
    ],
)
def test_nouveautes(depuis, jusqua, present, absent):
    n = maj.nouveautes(CHANGELOG, depuis, jusqua)
    assert all(s in n for s in present) and not any(s in n for s in absent)


def test_a_jour_rien_a_dire():
    assert maj.nouveautes(CHANGELOG, "1.3.0") == ""


def test_version_1_10_apres_1_9():
    assert maj._cle_version("1.10.0") > maj._cle_version("1.9.9")


EXEMPLE = {
    "identite": {"prenom": "A", "genre": "m"},
    "langues_parlees": ["fr"],
    "scoring": {"plafond_second": 10, "axes": {}},
    "_commentaire": "x",
    "neuf": {"x": 1},
}
MOI = {"identite": {"prenom": "B"}, "scoring": {"axes": {"a": 1}}}


def test_cles_manquantes_parent_cite_seul():
    assert maj.reglages_manquants(EXEMPLE, MOI) == [
        "identite.genre",
        "langues_parlees",
        "neuf",
        "scoring.plafond_second",
    ]


def test_cles_commentaire_ignorees():
    assert "_commentaire" not in maj.reglages_manquants(EXEMPLE, MOI)


def test_profil_complet_rien():
    assert maj.reglages_manquants(EXEMPLE, EXEMPLE) == []


@pytest.mark.parametrize(
    ("rel", "protege"),
    [
        ("profil/profil.json", True),
        ("Scripts/suivi.json", True),
        ("Mon_CV/cv.pdf", True),
        ("CV/x.docx", True),
        ("Lettres/a.docx", True),
        ("Scripts/apply_queue.json", True),
        ("Scripts/adzuna.json", True),
        ("profil/exemple_finance_esg.json", False),
        ("Scripts/ats_match.py", False),
        ("VERSION", False),
    ],
)
def test_protection_des_donnees(rel, protege):
    assert maj.protege(rel) is protege


# ── premiere mise a jour, sans manifeste ───────────────────────────────────────
@pytest.fixture
def premiere(installer, capsys):
    d = installer()
    ecrire(d, "Scripts/b.py", "B = 1  # ma modif\n")
    ecrire(d, "Scripts/vieux_modifie.py", "W = 99\n")
    ecrire(d, "Scripts/a_moi.py", "perso\n")
    ecrire(d, "Scripts/stable.py", "S = 1  # ma modif\n")
    ecrire(d, "profil/profil.json", '{"moi": 1}\n')
    rc, out = lancer(capsys)
    return d, rc, out


def _manifeste(d):
    return json.loads((d / ".maj_manifeste.json").read_text(encoding="utf-8"))


PREMIERE = [
    ("code 0", lambda d, rc, out: rc == 0),
    ("fichier intact remplace", lambda d, rc, out: lire(d, "Scripts/a.py") == "A = 2\n"),
    ("fichier modifie GARDE", lambda d, rc, out: lire(d, "Scripts/b.py") == "B = 1  # ma modif\n"),
    (
        "nouvelle version en .nouveau",
        lambda d, rc, out: lire(d, "Scripts/b.py.nouveau") == "B = 2\n",
    ),
    ("fichier ajoute", lambda d, rc, out: lire(d, "Scripts/nouveau.py") == "N = 1\n"),
    (
        "modifie chez moi, inchange en amont : garde",
        lambda d, rc, out: lire(d, "Scripts/stable.py") == "S = 1  # ma modif\n",
    ),
    ("sans .nouveau inutile", lambda d, rc, out: not (d / "Scripts/stable.py.nouveau").exists()),
    ("ni signale", lambda d, rc, out: "stable.py" not in out),
    ("fichier retire intact enleve", lambda d, rc, out: lire(d, "Scripts/vieux.py") is None),
    ("et sauvegarde", lambda d, rc, out: any(d.glob("_sauvegarde_maj/*/Scripts/vieux.py"))),
    (
        "fichier retire mais modifie garde",
        lambda d, rc, out: lire(d, "Scripts/vieux_modifie.py") == "W = 99\n",
    ),
    (
        "fichier de l'utilisateur jamais retire",
        lambda d, rc, out: lire(d, "Scripts/a_moi.py") == "perso\n",
    ),
    ("profil jamais ecrit", lambda d, rc, out: lire(d, "profil/profil.json") == '{"moi": 1}\n'),
    (
        "Mon_CV jamais ecrit",
        lambda d, rc, out: lire(d, "Mon_CV/LISEZ-MOI.txt") == "mets ton CV ici\n",
    ),
    (
        "sources_config intact remplace (reference connue)",
        lambda d, rc, out: lire(d, "Scripts/sources_config.json") == '{"v": 2}\n',
    ),
    ("VERSION passee a 1.3.0", lambda d, rc, out: maj.version_locale() == "1.3.0"),
    ("nouveautes affichees", lambda d, rc, out: "bouton de mise à jour" in out),
    ("reference = ZIP v1.2.0", lambda d, rc, out: "v1.2.0" in out),
    (
        "manifeste : b.py garde l'empreinte d'origine",
        lambda d, rc, out: _manifeste(d).get("Scripts/b.py") == maj._sha(b"B = 1\n"),
    ),
    ("manifeste : vieux.py oublie", lambda d, rc, out: "Scripts/vieux.py" not in _manifeste(d)),
]


@pytest.mark.parametrize("verif", [v for _, v in PREMIERE], ids=[n for n, _ in PREMIERE])
def test_premiere_mise_a_jour(premiere, verif):
    assert verif(*premiere)


def test_seconde_passe_deja_a_jour(premiere, capsys):
    assert "Déjà à jour" in lancer(capsys)[1]


def test_forcer_garde_toujours_la_modif(premiere, capsys):
    lancer(capsys, forcer=True)
    assert lire(premiere[0], "Scripts/b.py") == "B = 1  # ma modif\n"


# ── VERSION retouche a la main : remplace quand meme ───────────────────────────
@pytest.fixture
def version_retouchee(installer, capsys):
    d = installer()
    ecrire(d, "VERSION", "1.2.9\n")
    lancer(capsys)
    return d


def test_version_retouchee_remplacee(version_retouchee):
    assert maj.version_locale() == "1.3.0"


def test_pas_de_version_nouveau(version_retouchee):
    assert not (version_retouchee / "VERSION.nouveau").exists()


# ── sans reference (etiquette absente) : ancienne regle ────────────────────────
@pytest.fixture
def sans_reference(installer, capsys):
    d = installer(zips={maj.ZIP_URL: zip_de(V13)})
    ecrire(d, "Scripts/sources_config.json", '{"perso": 1}\n')
    return d, lancer(capsys)[0]


def test_sans_reference_code_0(sans_reference):
    assert sans_reference[1] == 0


def test_sources_config_presume_modifie_garde(sans_reference):
    assert lire(sans_reference[0], "Scripts/sources_config.json") == '{"perso": 1}\n'


def test_rien_n_est_retire_sans_reference(sans_reference):
    assert lire(sans_reference[0], "Scripts/vieux.py") == "V = 1\n"


# ── controle rate -> retour automatique ────────────────────────────────────────
@pytest.fixture
def controle_rate(installer, capsys):
    d = installer(controle=False)
    return d, lancer(capsys)[0]


RETOUR = [
    ("code 1", lambda d, rc: rc == 1),
    ("a.py retabli", lambda d, rc: lire(d, "Scripts/a.py") == "A = 1\n"),
    ("vieux.py retabli", lambda d, rc: lire(d, "Scripts/vieux.py") == "V = 1\n"),
    ("nouveau.py retire", lambda d, rc: lire(d, "Scripts/nouveau.py") is None),
    ("VERSION retablie", lambda d, rc: maj.version_locale() == "1.2.0"),
    ("pas de manifeste laisse", lambda d, rc: not (d / ".maj_manifeste.json").exists()),
]


@pytest.mark.parametrize("verif", [v for _, v in RETOUR], ids=[n for n, _ in RETOUR])
def test_controle_rate_retour_automatique(controle_rate, verif):
    assert verif(*controle_rate)


# ── panne en pleine ecriture -> retour automatique ─────────────────────────────
@pytest.fixture
def panne_ecriture(installer, capsys, monkeypatch):
    d = installer()
    vrai = Path.write_bytes

    def panne(self, data):
        if self.name == "nouveau.py":  # ajoute apres les remplacements
            raise PermissionError("verrouillé")
        return vrai(self, data)

    monkeypatch.setattr(Path, "write_bytes", panne)
    rc = lancer(capsys)[0]
    monkeypatch.setattr(Path, "write_bytes", vrai)
    return d, rc


PANNE = [
    ("code 1", lambda d, rc: rc == 1),
    ("a.py retabli", lambda d, rc: lire(d, "Scripts/a.py") == "A = 1\n"),
    ("VERSION retablie", lambda d, rc: maj.version_locale() == "1.2.0"),
    ("vieux.py jamais enleve", lambda d, rc: lire(d, "Scripts/vieux.py") == "V = 1\n"),
]


@pytest.mark.parametrize("verif", [v for _, v in PANNE], ids=[n for n, _ in PANNE])
def test_panne_en_pleine_ecriture(panne_ecriture, verif):
    assert verif(*panne_ecriture)


# ── --annuler ──────────────────────────────────────────────────────────────────
@pytest.fixture
def annulee(installer, capsys):
    d = installer()
    lancer(capsys)
    ecrire(d, "Scripts/nouveau.py", "N = 1  # retouché\n")
    rc = maj.annuler_zip()
    capsys.readouterr()
    return d, rc


ANNULER = [
    ("code 0", lambda d, rc: rc == 0),
    ("VERSION 1.2.0", lambda d, rc: maj.version_locale() == "1.2.0"),
    ("a.py retabli", lambda d, rc: lire(d, "Scripts/a.py") == "A = 1\n"),
    ("vieux.py revenu", lambda d, rc: lire(d, "Scripts/vieux.py") == "V = 1\n"),
    (
        "ajout retouche par l'utilisateur laisse",
        lambda d, rc: lire(d, "Scripts/nouveau.py") == "N = 1  # retouché\n",
    ),
]


@pytest.mark.parametrize("verif", [v for _, v in ANNULER], ids=[n for n, _ in ANNULER])
def test_annuler(annulee, verif):
    assert verif(*annulee)


def test_seconde_annulation_rien_a_annuler(annulee):
    assert maj.annuler_zip() == 1


def test_la_mise_a_jour_se_refait_apres_annulation(annulee, capsys):
    lancer(capsys)
    assert maj.version_locale() == "1.3.0"


# ── installe depuis le ZIP de main (≠ etiquette) : l'empreinte de l'installeur ─
@pytest.fixture
def main_entre_deux(installer):
    d = installer({**V12, "Scripts/a.py": "A = 1.5\n"})  # main a bouge apres la 1.2.0
    ecrire(d, "Scripts/_logs/x.log", "log\n")
    return d, maj.initialiser()


def test_initialiser_ecrit_l_empreinte(main_entre_deux):
    assert main_entre_deux[1] is True


def test_empreinte_des_fichiers_du_programme(main_entre_deux):
    assert _manifeste(main_entre_deux[0]).get("Scripts/a.py") == maj._sha(b"A = 1.5\n")


def test_empreinte_sans_journaux_ni_donnees(main_entre_deux):
    assert not any(
        k.startswith(("Scripts/_logs", "Mon_CV")) for k in _manifeste(main_entre_deux[0])
    )


def test_initialiser_une_seconde_fois_rien(main_entre_deux):
    assert maj.initialiser() is False


def test_non_modifie_remplace_malgre_l_ecart_a_l_etiquette(main_entre_deux, capsys):
    lancer(capsys)
    assert lire(main_entre_deux[0], "Scripts/a.py") == "A = 2\n"


def test_pas_de_nouveau_pour_l_ecart_a_l_etiquette(main_entre_deux, capsys):
    lancer(capsys)
    assert not (main_entre_deux[0] / "Scripts/a.py.nouveau").exists()


def test_initialiser_ne_fait_rien_dans_un_depot_git(installer):
    d = installer()
    (d / ".git").mkdir()
    assert maj.initialiser() is False


# ── sans VERSION (copie de developpement) : rien n'est tente ───────────────────
@pytest.fixture
def sans_version(installer, capsys, monkeypatch):
    d = installer({k: v for k, v in V12.items() if k != "VERSION"}, zips={})
    monkeypatch.setattr(sys, "argv", ["mise_a_jour.py"])
    rc = maj.main()
    return d, rc, capsys.readouterr().out


def test_sans_version_code_1(sans_version):
    assert sans_version[1] == 1


def test_sans_version_message_clair(sans_version):
    assert "Pas de fichier VERSION" in sans_version[2]


def test_sans_version_aucun_fichier_ecrit(sans_version):
    assert sorted(p.name for p in sans_version[0].iterdir()) == ["Mon_CV", "Scripts"]


# ── verification seule ─────────────────────────────────────────────────────────
@pytest.fixture
def verification(installer, capsys):
    installer()
    return lancer(capsys, verifier=True)[1]


def test_verifier_annonce_la_mise_a_jour(verification):
    assert "Mise à jour disponible" in verification


def test_verifier_montre_les_nouveautes(verification):
    assert "bouton de mise à jour" in verification


def test_verifier_ne_touche_a_rien(verification):
    assert maj.version_locale() == "1.2.0"


# ── controle reel sur ce depot ─────────────────────────────────────────────────
def test_tous_les_scripts_se_chargent(capsys):
    assert maj.controler()


def test_le_controle_du_nouvel_arbre_passe_par_son_propre_code(capsys):
    # `python -m jobhunter maj --controler` : l'entree stable que l'ancienne version
    # appelle apres avoir remplace les fichiers.
    assert maj.controler_nouveau()
    assert "tous les scripts se chargent" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("sortie", "attendu"),
    [(r'<Command>"C:\py.exe" "D:\JH\Scripts\pipeline_quotidien.py"</Command>', True), ("", False)],
)
def test_une_tache_planifiee_qui_vise_l_ancien_pipeline_est_signalee(
    monkeypatch, capsys, sortie, attendu
):
    monkeypatch.setattr(
        maj.subprocess,
        "run",
        lambda *a, **k: maj.subprocess.CompletedProcess(a, 0 if sortie else 1, sortie, ""),
    )
    assert maj.signaler_tache_ancienne() is attendu
    assert ("Relance" in capsys.readouterr().out) is attendu
