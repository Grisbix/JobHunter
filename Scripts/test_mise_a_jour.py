#!/usr/bin/env python3
"""test_mise_a_jour.py — La mise a jour ne doit jamais perdre ce que l'utilisateur a fait.

Hors reseau : les ZIP « GitHub » sont fabriques en memoire et servis a la place
du telechargement, l'installation vit dans un dossier temporaire. On y verifie :

  - un fichier modifie par l'utilisateur n'est pas ecrase, MEME a la premiere
    mise a jour (sans manifeste : la reference est le ZIP de la version installee) ;
    c'etait le trou de la 1.2.0, mesure sur une vraie installation ;
  - un fichier retire du programme part s'il est intact, reste s'il est modifie,
    et un fichier cree par l'utilisateur n'est jamais retire ;
  - les donnees (profil, suivi, CV) ne sont jamais ecrites ;
  - un controle rate remet la version d'avant, tout comme --annuler ;
  - les nouveautes et les nouveaux reglages du profil sont bien extraits.

Run : python test_mise_a_jour.py
"""

import _profil_test  # noqa: F401  — les tests tournent sur le profil d'exemple

import argparse
import contextlib
import io
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import mise_a_jour as maj

PASS = FAIL = 0


def check(nom, obtenu, attendu=True):
    global PASS, FAIL
    if obtenu == attendu:
        PASS += 1
        print(f"  ✅ {nom}")
    else:
        FAIL += 1
        print(f"  ❌ {nom}\n       obtenu {obtenu!r}, attendu {attendu!r}")


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


@contextlib.contextmanager
def installation(fichiers):
    """Dossier temporaire installe avec `fichiers`, mise_a_jour pointe dessus."""
    d = Path(tempfile.mkdtemp(prefix="maj_test_"))
    for rel, txt in fichiers.items():
        (d / rel).parent.mkdir(parents=True, exist_ok=True)
        (d / rel).write_text(txt, encoding="utf-8", newline="")
    sauf = {
        k: getattr(maj, k)
        for k in ("RACINE", "MANIFESTE", "SAUVEGARDES", "GIT_AVANT", "_get", "controler", "apres")
    }
    maj.RACINE, maj.MANIFESTE = d, d / ".maj_manifeste.json"
    maj.SAUVEGARDES, maj.GIT_AVANT = d / "_sauvegarde_maj", d / ".maj_git_avant"
    maj.apres = lambda changes_requirements: 0  # ni pip ni profil reel
    try:
        yield d
    finally:
        for k, v in sauf.items():
            setattr(maj, k, v)
        shutil.rmtree(d, ignore_errors=True)


def servir(zips):
    def _get(url, timeout):
        if url not in zips:
            raise OSError(f"404 {url}")
        return zips[url]

    maj._get = _get


def lancer(verifier=False, forcer=False):
    args = argparse.Namespace(verifier=verifier, forcer=forcer, annuler=False)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = maj.par_zip(args)
    return rc, out.getvalue()


def lire(d, rel):
    p = d / rel
    return p.read_text(encoding="utf-8") if p.exists() else None


ZIPS = {maj.ZIP_URL: zip_de(V13), maj.TAG_URL.format("1.2.0"): zip_de(V12, "JobHunter-1.2.0")}

print("── Nouveautés (CHANGELOG)")
n = maj.nouveautes(CHANGELOG, "1.2.0")
check("1.2.0 → voit 1.3.0", "1.3.0" in n and "bouton" in n)
check("1.2.0 → ne revoit pas 1.2.0", "plafond" in n, False)
check(
    "1.1.0 → voit 1.3.0 et 1.2.0",
    all(s in maj.nouveautes(CHANGELOG, "1.1.0") for s in ("bouton", "plafond")),
)
check("jusqu'à 1.2.0 exclut 1.3.0", "bouton" in maj.nouveautes(CHANGELOG, "1.1.0", "1.2.0"), False)
check("à jour → rien", maj.nouveautes(CHANGELOG, "1.3.0"), "")
check("titre du fichier jamais repris", "# Nouveautés" in maj.nouveautes(CHANGELOG, "0"), False)
check("version 1.10 > 1.9", maj._cle_version("1.10.0") > maj._cle_version("1.9.9"))

print("── Nouveaux réglages du profil")
ex = {
    "identite": {"prenom": "A", "genre": "m"},
    "langues_parlees": ["fr"],
    "scoring": {"plafond_second": 10, "axes": {}},
    "_commentaire": "x",
    "neuf": {"x": 1},
}
moi = {"identite": {"prenom": "B"}, "scoring": {"axes": {"a": 1}}}
check(
    "clés manquantes, parent cité seul",
    maj.reglages_manquants(ex, moi),
    ["identite.genre", "langues_parlees", "neuf", "scoring.plafond_second"],
)
check("clés « _commentaire » ignorées", "_commentaire" in maj.reglages_manquants(ex, moi), False)
check("profil complet → rien", maj.reglages_manquants(ex, ex), [])

print("── Protection des données")
for rel in (
    "profil/profil.json",
    "Scripts/suivi.json",
    "Mon_CV/cv.pdf",
    "CV/x.docx",
    "Lettres/a.docx",
    "Scripts/apply_queue.json",
    "Scripts/adzuna.json",
):
    check(f"protégé : {rel}", maj.protege(rel))
for rel in ("profil/exemple_finance_esg.json", "Scripts/ats_match.py", "VERSION"):
    check(f"programme : {rel}", maj.protege(rel), False)

print("── Première mise à jour, sans manifeste")
with installation(V12) as d:
    (d / "Scripts/b.py").write_text("B = 1  # ma modif\n", encoding="utf-8", newline="")
    (d / "Scripts/vieux_modifie.py").write_text("W = 99\n", encoding="utf-8", newline="")
    (d / "Scripts/a_moi.py").write_text("perso\n", encoding="utf-8", newline="")
    (d / "Scripts/stable.py").write_text("S = 1  # ma modif\n", encoding="utf-8", newline="")
    (d / "profil/profil.json").parent.mkdir(exist_ok=True)
    (d / "profil/profil.json").write_text('{"moi": 1}\n', encoding="utf-8", newline="")
    servir(ZIPS)
    maj.controler = lambda: True
    rc, out = lancer()
    check("code 0", rc, 0)
    check("fichier intact remplacé", lire(d, "Scripts/a.py"), "A = 2\n")
    check(
        "fichier modifié GARDÉ (trou de la 1.2.0)", lire(d, "Scripts/b.py"), "B = 1  # ma modif\n"
    )
    check("… nouvelle version posée en .nouveau", lire(d, "Scripts/b.py.nouveau"), "B = 2\n")
    check("fichier ajouté", lire(d, "Scripts/nouveau.py"), "N = 1\n")
    check(
        "modifié chez moi, inchangé en amont : gardé",
        lire(d, "Scripts/stable.py"),
        "S = 1  # ma modif\n",
    )
    check("… sans .nouveau inutile", (d / "Scripts/stable.py.nouveau").exists(), False)
    check("… ni signalé", "stable.py" in out, False)
    check("fichier retiré intact → enlevé", lire(d, "Scripts/vieux.py"), None)
    check("… et sauvegardé", any(d.glob("_sauvegarde_maj/*/Scripts/vieux.py")))
    check("fichier retiré mais modifié → gardé", lire(d, "Scripts/vieux_modifie.py"), "W = 99\n")
    check("fichier de l'utilisateur jamais retiré", lire(d, "Scripts/a_moi.py"), "perso\n")
    check("profil jamais écrit", lire(d, "profil/profil.json"), '{"moi": 1}\n')
    check("Mon_CV jamais écrit", lire(d, "Mon_CV/LISEZ-MOI.txt"), "mets ton CV ici\n")
    check(
        "sources_config intact remplacé (référence connue)",
        lire(d, "Scripts/sources_config.json"),
        '{"v": 2}\n',
    )
    check("VERSION passée à 1.3.0", maj.version_locale(), "1.3.0")
    check("nouveautés affichées", "bouton de mise à jour" in out)
    check("référence = ZIP v1.2.0", "v1.2.0" in out)
    m = json.loads((d / ".maj_manifeste.json").read_text(encoding="utf-8"))
    check(
        "manifeste : b.py garde l'empreinte d'origine", m.get("Scripts/b.py"), maj._sha(b"B = 1\n")
    )
    check("manifeste : vieux.py oublié", "Scripts/vieux.py" in m, False)

    print("── Seconde passe : déjà à jour, puis --forcer")
    rc, out = lancer()
    check("déjà à jour", "Déjà à jour" in out)
    lancer(forcer=True)
    check("--forcer : b.py toujours gardé", lire(d, "Scripts/b.py"), "B = 1  # ma modif\n")

print("── VERSION retouché à la main : remplacé quand même")
with installation(V12) as d:
    (d / "VERSION").write_text("1.2.9\n", encoding="utf-8", newline="")
    servir(ZIPS)
    maj.controler = lambda: True
    rc, out = lancer()
    check("VERSION passée à 1.3.0", maj.version_locale(), "1.3.0")
    check("pas de VERSION.nouveau", (d / "VERSION.nouveau").exists(), False)

print("── Sans référence (étiquette absente) : ancienne règle")
with installation(V12) as d:
    (d / "Scripts/sources_config.json").write_text('{"perso": 1}\n', encoding="utf-8", newline="")
    servir({maj.ZIP_URL: zip_de(V13)})
    maj.controler = lambda: True
    rc, out = lancer()
    check("code 0", rc, 0)
    check(
        "sources_config présumé modifié → gardé",
        lire(d, "Scripts/sources_config.json"),
        '{"perso": 1}\n',
    )
    check("rien n'est retiré sans référence", lire(d, "Scripts/vieux.py"), "V = 1\n")

print("── Contrôle raté → retour automatique")
with installation(V12) as d:
    servir(ZIPS)
    maj.controler = lambda: False
    rc, out = lancer()
    check("code 1", rc, 1)
    check("a.py rétabli", lire(d, "Scripts/a.py"), "A = 1\n")
    check("vieux.py rétabli", lire(d, "Scripts/vieux.py"), "V = 1\n")
    check("nouveau.py retiré", lire(d, "Scripts/nouveau.py"), None)
    check("VERSION rétablie", maj.version_locale(), "1.2.0")
    check(
        "pas de manifeste laissé (il n'y en avait pas)", (d / ".maj_manifeste.json").exists(), False
    )

print("── Panne en pleine écriture → retour automatique")
with installation(V12) as d:
    servir(ZIPS)
    maj.controler = lambda: True
    vrai = Path.write_bytes

    def panne(self, data):
        if self.name == "nouveau.py":  # ajoute apres les remplacements
            raise PermissionError("verrouillé")
        return vrai(self, data)

    Path.write_bytes = panne
    try:
        rc, out = lancer()
    finally:
        Path.write_bytes = vrai
    check("code 1", rc, 1)
    check("a.py rétabli", lire(d, "Scripts/a.py"), "A = 1\n")
    check("VERSION rétablie", maj.version_locale(), "1.2.0")
    check("vieux.py jamais enlevé", lire(d, "Scripts/vieux.py"), "V = 1\n")

print("── --annuler")
with installation(V12) as d:
    servir(ZIPS)
    maj.controler = lambda: True
    lancer()
    (d / "Scripts/nouveau.py").write_text("N = 1  # retouché\n", encoding="utf-8", newline="")
    with contextlib.redirect_stdout(io.StringIO()):
        rc = maj.annuler_zip()
    check("code 0", rc, 0)
    check("VERSION 1.2.0", maj.version_locale(), "1.2.0")
    check("a.py rétabli", lire(d, "Scripts/a.py"), "A = 1\n")
    check("vieux.py revenu", lire(d, "Scripts/vieux.py"), "V = 1\n")
    check(
        "ajout retouché par l'utilisateur laissé",
        lire(d, "Scripts/nouveau.py"),
        "N = 1  # retouché\n",
    )
    with contextlib.redirect_stdout(io.StringIO()):
        check("seconde annulation : rien à annuler", maj.annuler_zip(), 1)
    rc, out = lancer()
    check("la mise à jour se refait après annulation", maj.version_locale(), "1.3.0")

print("── Installé depuis le ZIP de main (≠ étiquette) : l'empreinte de l'installeur fait foi")
MAIN_ENTRE_DEUX = {**V12, "Scripts/a.py": "A = 1.5\n"}  # main a bouge apres la release 1.2.0
with installation(MAIN_ENTRE_DEUX) as d:
    (d / "Scripts/_logs").mkdir()
    (d / "Scripts/_logs/x.log").write_text("log\n", encoding="utf-8", newline="")
    check("--initialiser écrit l'empreinte", maj.initialiser())
    m = json.loads((d / ".maj_manifeste.json").read_text(encoding="utf-8"))
    check("… des fichiers du programme", m.get("Scripts/a.py"), maj._sha(b"A = 1.5\n"))
    check(
        "… sans les journaux ni les données",
        any(k.startswith(("Scripts/_logs", "Mon_CV")) for k in m),
        False,
    )
    check("une seconde fois : rien (déjà un manifeste)", maj.initialiser(), False)
    servir(ZIPS)
    maj.controler = lambda: True
    rc, out = lancer()
    check(
        "a.py (non modifié) remplacé malgré l'écart à l'étiquette",
        lire(d, "Scripts/a.py"),
        "A = 2\n",
    )
    check("pas de .nouveau", (d / "Scripts/a.py.nouveau").exists(), False)
with installation(V12) as d:
    (d / ".git").mkdir()
    check("--initialiser ne fait rien dans un dépôt git", maj.initialiser(), False)

print("── Sans VERSION (copie de développement) : rien n'est tenté")
with installation({k: v for k, v in V12.items() if k != "VERSION"}) as d:
    servir({})
    maj.controler = lambda: True
    sys.argv = ["mise_a_jour.py"]
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        rc = maj.main()
    check("code 1", rc, 1)
    check("message clair", "Pas de fichier VERSION" in buf.getvalue())
    check("aucun fichier écrit", sorted(p.name for p in d.iterdir()), sorted({"Scripts", "Mon_CV"}))

print("── Vérification seule")
with installation(V12) as d:
    servir(ZIPS)
    maj.controler = lambda: True
    rc, out = lancer(verifier=True)
    check("annonce la mise à jour", "Mise à jour disponible" in out)
    check("montre les nouveautés", "bouton de mise à jour" in out)
    check("ne touche à rien", maj.version_locale(), "1.2.0")

print("── Contrôle réel sur ce dépôt")
with contextlib.redirect_stdout(io.StringIO()):
    ok = maj.controler()
check("tous les scripts se chargent", ok)

print(f"\n=== BILAN : {PASS} ✅  /  {FAIL} ❌  ({PASS}/{PASS + FAIL}) ===")
sys.exit(1 if FAIL else 0)
