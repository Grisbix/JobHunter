#!/usr/bin/env python3
"""acces.py — Gere les ACCES aux sites, SANS jamais stocker de mot de passe.

POURQUOI PAS DE MOTS DE PASSE ICI
Un fichier de mots de passe en clair a cote du code, c'est le pire endroit
possible : synchronise par OneDrive, lisible par tout programme du PC, et un
jour commite par erreur. Chrome a deja un gestionnaire de mots de passe
chiffre par le systeme — c'est LUI qui doit remplir les formulaires.

COMMENT LES PROGRAMMES "OUVRENT TOUT"
acces.py et apply_runner partagent un profil Chrome dedie et persistant.
Tu te connectes a la main via --open ; apply_runner reutilise ensuite ce
profil, avec ou sans --chrome, sans le remplacer par ton Chrome quotidien.
Les autres collecteurs ont leurs propres options de profil.
Aucun mot de passe ne transite par le code.

CE QUE CE FICHIER GARDE
  - l'URL de connexion de chaque site
  - l'identifiant (email) utilise — pas le mot de passe
  - l'etat de la session vu au dernier controle
  - les CLES D'API (secrets non-mots-de-passe : France Travail...), saisies
    masquees et jamais affichees

Run :
  python JobHunter.pyw acces --list                    # etat des acces
  python JobHunter.pyw acces --open linkedin.com       # ouvre la page de connexion dans TON Chrome
  python JobHunter.pyw acces --check                   # teste quelles sessions sont encore actives
  python JobHunter.pyw acces --set-id linkedin.com --email moi@x.fr
  python JobHunter.pyw acces --set-key francetravail   # saisie masquee d'une cle d'API
"""

import argparse
import datetime
import getpass
import importlib
import json
import sys
import time
from pathlib import Path

from jobhunter import racine as _racine

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

HERE = _racine.scripts()
COMPTES = HERE / "comptes.json"
KEYS = HERE / "api_keys.json"  # gitignore : contient des secrets

# MEME profil que apply_runner : les sessions ouvertes ici sont celles que les
# scripts retrouveront. Pointer sur la racine « User Data » de Chrome ne marche
# PAS — Chrome relance une autre instance et lache Playwright (TargetClosedError).
# Un profil dedie evite aussi d'avoir a fermer le Chrome de tous les jours.
import os as _os

PROFIL = Path(_os.environ.get("LOCALAPPDATA", str(Path.home()))) / "apply_runner_chrome"

# Sites ou une session connectee change ce qu'on peut faire.
SITES_CONNEXION = {
    "linkedin.com": "https://www.linkedin.com/login",
    "welcometothejungle.com": "https://www.welcometothejungle.com/fr/signin",
    "mon-vie-via.businessfrance.fr": "https://mon-vie-via.businessfrance.fr/",
    "glassdoor.fr": "https://www.glassdoor.fr/profile/login_input.htm",
    "apec.fr": "https://www.apec.fr/candidat/connexion.html",
    "francetravail.fr": "https://candidat.francetravail.fr/espacepersonnel/",
}


def _load(p, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save(p, obj):
    importlib.import_module("jobhunter.programmes.jutil").jwrite(p, obj)


def cmd_list():
    c = _load(COMPTES, {})
    k = _load(KEYS, {})
    print(f"{'SITE':<34}{'IDENTIFIANT':<26}{'SESSION':<12}VERIFIE")
    for host, login in SITES_CONNEXION.items():
        e = c.get(host) or {}
        print(
            f"  {host:<32}{str(e.get('identifiant') or '—')[:24]:<26}"
            f"{str(e.get('session') or '?'):<12}{str(e.get('session_verif') or '—')}"
        )
    print(f"\nCLES D'API ({KEYS.name}) — valeurs jamais affichees :")
    if not k:
        print("  (aucune)")
    for nom, v in k.items():
        champs = ", ".join(sorted(v)) if isinstance(v, dict) else "valeur"
        print(f"  ✓ {nom:<24} [{champs}]")
    print("\nLes MOTS DE PASSE restent dans le gestionnaire de Chrome — jamais ici.")
    return 0


# Duree max d'attente d'une connexion manuelle, en minutes.
ATTENTE_MIN = 15


def _procs_profil():
    """(pid, ppid) des Chrome lances sur LE profil dedie, et eux seuls.

    On filtre sur --user-data-dir dans la ligne de commande : tuer chrome.exe
    en masse fermerait le navigateur personnel de l'utilisateur, avec ses
    onglets et ses formulaires en cours. Jamais.
    """
    import subprocess

    ps = (
        "Get-CimInstance Win32_Process | Where-Object { "
        "$_.Name -eq 'chrome.exe' -and $_.CommandLine -like '*apply_runner_chrome*' } | "
        "ForEach-Object { [string]$_.ProcessId + ' ' + [string]$_.ParentProcessId }"
    )
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=30
        )
    except Exception:
        return []
    out = []
    for ligne in r.stdout.split(chr(10)):
        m = ligne.split()
        if len(m) == 2 and m[0].isdigit() and m[1].isdigit():
            out.append((int(m[0]), int(m[1])))
    return out


def _pids_profil():
    return [pid for pid, _ in _procs_profil()]


def _racines_profil():
    """Les processus Chrome RACINE du profil (parent hors Chrome).

    Seule la racine possede une fenetre. taskkill sans /F envoie WM_CLOSE, qui
    n'atteint que les processus a fenetre : viser les enfants (renderers, GPU)
    ne ferme rien du tout. C'est la racine qu'il faut prier de se fermer, et
    elle entraine ses enfants en s'arretant proprement — donc en ecrivant ses
    cookies sur disque.
    """
    procs = _procs_profil()
    connus = {pid for pid, _ in procs}
    return [pid for pid, ppid in procs if ppid not in connus]


def cmd_close(force=False):
    """Ferme les Chrome restes ouverts sur le profil dedie.

    Sert a deverrouiller le profil : tant qu'un Chrome le tient, --check ne peut
    pas le lire et les cookies ne sont pas garantis ecrits sur disque.
    On envoie d'abord une fermeture NORMALE (taskkill sans /F ferme les fenetres
    proprement, Chrome vide alors ses caches). /F seulement en dernier recours,
    et uniquement sur --force.
    """
    import subprocess

    pids = _pids_profil()
    if not pids:
        print("✓ aucun Chrome sur le profil dedie — rien a fermer")
        return 0
    racines = _racines_profil() or pids
    print(
        f"→ {len(pids)} processus sur le profil dedie ({len(racines)} racine(s)) : fermeture normale"
    )
    for pid in racines:
        try:
            subprocess.run(["taskkill", "/PID", str(pid), "/T"], capture_output=True, timeout=15)
        except Exception:
            pass
    for _ in range(10):
        time.sleep(1)
        if not _pids_profil():
            print("✓ profil libere (fermeture propre)")
            return 0
    restants = _pids_profil()
    if not force:
        print(
            f"⚠ {len(restants)} processus resistent. Relance avec --close --force"
            " (les cookies non encore ecrits seraient perdus)."
        )
        return 1
    print(f"→ {len(restants)} recalcitrants : arret force")
    for pid in restants:
        try:
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid), "/T"], capture_output=True, timeout=15
            )
        except Exception:
            pass
    time.sleep(1)
    reste = _pids_profil()
    print("✓ profil libere" if not reste else f"✗ {len(reste)} processus tiennent encore")
    return 0 if not reste else 1


def cmd_open(host):
    """Ouvre la page de connexion dans TON Chrome. Tu te connectes a la main ;
    Chrome retient, et --chrome reutilisera la session."""
    url = SITES_CONNEXION.get(host)
    if not url:
        print(f"✗ site inconnu. Connus : {', '.join(SITES_CONNEXION)}")
        return 1
    # Ouvrir dans le navigateur PAR DEFAUT enregistrerait la session dans le
    # profil de tous les jours — invisible pour les scripts. On ouvre donc le
    # profil dedie, celui que apply_runner et --check utilisent.
    try:
        from jobhunter.navigation import get_sync_playwright

        sp, _ = get_sync_playwright("auto")
    except Exception:
        from playwright.sync_api import sync_playwright as sp
    PROFIL.mkdir(parents=True, exist_ok=True)
    print(f"→ ouverture de {url}")
    print(f"  profil : {PROFIL}")
    print("  Connecte-toi dans la fenetre, puis FERME-LA : la session est conservee.")
    with sp() as p:
        try:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=str(PROFIL),
                channel="chrome",
                headless=False,
                args=["--no-first-run", "--no-default-browser-check"],
                no_viewport=True,
                timeout=90000,
            )
        except Exception as e:
            print(f"✗ Chrome n'a pas demarre ({type(e).__name__})")
            return 1
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(url, timeout=45000)
        except Exception:
            pass
        # Attente ACTIVE : on relit l'etat de session toutes les 2 s et on ferme
        # des que la connexion est faite. Plus besoin d'un humain pour fermer la
        # fenetre, ni d'un stdin utilisable (input() leve EOFError sous un agent,
        # et isatty() ment : il renvoie True alors que stdin est deja ferme).
        print(f"  Attente de la connexion (jusqu a {ATTENTE_MIN} min)...")
        fin = time.time() + ATTENTE_MIN * 60
        connecte = False
        while time.time() < fin:
            if not ctx.pages:  # fenetre fermee a la main = fini
                break
            try:
                if ctx.pages[0].evaluate(_SESSION_JS):
                    connecte = True
                    break
                ctx.pages[0].wait_for_timeout(2000)
            except Exception:
                # Une redirection OAuth détruit temporairement le contexte JS.
                # Attendre le prochain tour, sans fermer la connexion en cours.
                if not ctx.pages:
                    break
                time.sleep(2)
        if connecte:
            print("  ✓ connexion detectee — fermeture propre (les cookies sont ecrits sur disque)")
        elif ctx.pages:
            print("  ⚠ delai ecoule sans connexion detectee — fermeture quand meme")
        try:
            ctx.close()
        except Exception:
            pass
    if connecte:
        print(
            "→ connexion détectée, profil conservé. Vérifie avec : python JobHunter.pyw acces --check"
        )
        return 0
    print(
        "→ connexion non confirmée ; profil conservé. Vérifie avec : python JobHunter.pyw acces --check"
    )
    return 4


_SESSION_JS = r"""
() => {
  const N = s => (s||'').toLowerCase();
  // liens/boutons qui n'existent QUE pour un utilisateur connecte
  const rx = /(se deconnecter|se déconnecter|deconnexion|déconnexion|log ?out|sign ?out)/;
  const els = [...document.querySelectorAll('a,button,[role=button]')];
  // Un bouton public « Mon compte » ou un avatar ne prouve pas une connexion.
  if (els.some(e => e.getClientRects().length &&
      getComputedStyle(e).visibility !== 'hidden' &&
      rx.test(N(e.innerText) + ' ' + N(e.getAttribute('aria-label'))))) return true;
  return false;
}
"""


def cmd_check(limit_hosts=None):
    """Ouvre chaque site avec le profil Chrome reel et regarde si on est connecte.
    Ne saisit RIEN : lecture seule de l'etat de session."""
    # Un Chrome encore ouvert TIENT le profil : launch_persistent_context echoue
    # ou demarre sur un profil incomplet. On libere d'abord, proprement.
    if _pids_profil():
        print("→ profil occupe par un Chrome ouvert : fermeture prealable")
        cmd_close(force=False)
    c = _load(COMPTES, {})
    hosts = [h for h in SITES_CONNEXION if not limit_hosts or h in limit_hosts]
    try:
        from jobhunter.navigation import analyze, dismiss_cookies, get_sync_playwright

        sp, eng = get_sync_playwright("auto")
    except Exception as e:
        print(f"✗ playwright indisponible : {type(e).__name__}")
        return 1
    PROFIL.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    with sp() as p:
        try:
            # PAS de --disable-blink-features ici : ce flag declenche la banniere
            # « Vous utilisez un indicateur de ligne de commande non pris en
            # charge ». Ce script ne fait que LIRE un etat de session, il n'a
            # aucun besoin de furtivite.
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=str(PROFIL),
                channel="chrome",
                headless=False,
                args=["--no-first-run", "--no-default-browser-check"],
                no_viewport=True,
                timeout=90000,
            )
        except Exception as e:
            # Distinguer les deux causes : le message precedent annoncait
            # « profil verrouille » meme sur un simple depassement de delai.
            n = type(e).__name__
            if "Timeout" in n:
                print("✗ Chrome trop lent a demarrer (90 s depasses).")
                print("  Souvent du a une session Chrome fantome : verifie qu'aucun")
                print("  processus chrome.exe ne subsiste, puis relance.")
            else:
                print(f"✗ Chrome n'a pas demarre sur {PROFIL.name}.")
            print(f"  ({n})")
            return 1
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        for h in hosts:
            try:
                page.goto(SITES_CONNEXION[h], timeout=25000, wait_until="domcontentloaded")
                # La banniere de consentement masque la page et fausse analyze().
                # COOKIE_JS cherche « Tout refuser » en priorite (OneTrust, Didomi,
                # Axeptio, tarteaucitron) : option la plus respectueuse de la vie privee.
                try:
                    dismiss_cookies(page)
                    page.wait_for_timeout(700)
                except Exception:
                    pass
                a = analyze(page)
                kind = str(a.get("kind") or "?")
                # Un formulaire de connexion OU d'inscription = pas connecte.
                # (« register » etait compte comme connecte : LinkedIn et Indeed
                # ressortaient « connecte » alors qu'ils affichaient une inscription.)
                if a.get("blocked") or a.get("captcha"):
                    etat = "bloque"
                elif kind in ("login", "register"):
                    etat = "deconnecte"
                else:
                    # Absence de formulaire ne prouve rien : on cherche un signe
                    # POSITIF de session (deconnexion, avatar, espace perso).
                    etat = "connecte" if page.evaluate(_SESSION_JS) else "indetermine"
            except Exception as ex:
                etat, kind = "erreur", type(ex).__name__
            entree = c.setdefault(h, {})
            entree["session"], entree["session_verif"] = etat, today
            print(f"  {etat:<12} {h:<34} (kind={kind})")
        try:
            ctx.close()
        except Exception:
            pass
    _save(COMPTES, c)
    print(f"\n→ etat ecrit dans {COMPTES.name}")
    return 0


def cmd_open_all(only=None):
    """Ouvre CHAQUE page de connexion dans son propre onglet, sur le profil dedie,
    et laisse le navigateur ouvert pour que tu te connectes site par site.

    Pas d'input() ici : lance en tache de fond, stdin est ferme et un input()
    provoquerait un EOFError qui refermerait aussitot le navigateur. On attend
    donc que TU fermes les onglets — le script se termine quand il n'en reste
    plus, et Chrome a alors ecrit les sessions sur disque.
    """
    import time as _t

    try:
        from jobhunter.navigation import get_sync_playwright

        sp, _ = get_sync_playwright("auto")
    except Exception:
        from playwright.sync_api import sync_playwright as sp
    PROFIL.mkdir(parents=True, exist_ok=True)
    sites = [(h, u) for h, u in SITES_CONNEXION.items() if not only or h in only]
    print(f"Profil : {PROFIL}")
    print(f"{len(sites)} onglet(s) — connecte-toi dans chacun, puis FERME les onglets.")
    with sp() as p:
        try:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=str(PROFIL),
                channel="chrome",
                headless=False,
                args=["--no-first-run", "--no-default-browser-check"],
                no_viewport=True,
                timeout=90000,
            )
        except Exception as e:
            print(f"✗ Chrome n'a pas demarre ({type(e).__name__})")
            return 1
        first = ctx.pages[0] if ctx.pages else None
        for i, (h, u) in enumerate(sites):
            page = first if (i == 0 and first) else ctx.new_page()
            try:
                page.goto(u, timeout=45000, wait_until="domcontentloaded")
                # Ecarte le bandeau cookies (refus prioritaire) pour que tu arrives
                # directement sur le formulaire de connexion.
                try:
                    from jobhunter.navigation import dismiss_cookies as _dc

                    _dc(page)
                    page.wait_for_timeout(700)
                except Exception:
                    pass
                print(f"  ✓ onglet {i + 1}/{len(sites)} : {h}")
            except Exception as ex:
                print(f"  ! onglet {i + 1}/{len(sites)} : {h} ({type(ex).__name__})")
            _t.sleep(0.6)
        print("\nNavigateur ouvert. Connecte-toi dans chaque onglet.")
        print("Quand tu fermes le dernier onglet, la session est enregistree.")
        try:
            while ctx.pages:  # tient tant qu'un onglet reste ouvert
                _t.sleep(3)
        except Exception:
            pass
        try:
            ctx.close()
        except Exception:
            pass
    print("→ navigateur ferme, sessions conservees. Verifie : python JobHunter.pyw acces --check")
    return 0


def cmd_set_id(host, email):
    c = _load(COMPTES, {})
    c.setdefault(host, {})["identifiant"] = email
    _save(COMPTES, c)
    print(f"✓ identifiant enregistre pour {host} (aucun mot de passe stocke)")
    return 0


def cmd_set_key(nom):
    """Saisie MASQUEE d'une cle d'API. Valeur jamais affichee ni journalisee."""
    print(f"Cle d'API « {nom} » — saisie masquee, valeur jamais reaffichee.")
    champs = {}
    while True:
        c = input("  nom du champ (vide = terminer) : ").strip()
        if not c:
            break
        champs[c] = getpass.getpass(f"  {c} : ").strip()
    if not champs:
        print("✗ rien saisi.")
        return 1
    k = _load(KEYS, {})
    k[nom] = champs
    _save(KEYS, k)
    print(f"✓ {nom} enregistre dans {KEYS.name} ({len(champs)} champ(s)) — fichier ignore par git")
    return 0


def get_key(nom):
    """Lecture programmatique d'une cle (pour les autres scripts)."""
    return (_load(KEYS, {}) or {}).get(nom)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--open", metavar="HOST")
    ap.add_argument("--check", action="store_true")
    ap.add_argument(
        "--close", action="store_true", help="ferme les Chrome du profil dedie (libere le verrou)"
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="avec --close : arret force si la fermeture normale echoue",
    )
    ap.add_argument(
        "--open-all", action="store_true", help="ouvre TOUTES les pages de connexion en onglets"
    )
    ap.add_argument("--set-id", metavar="HOST")
    ap.add_argument("--email")
    ap.add_argument("--set-key", metavar="NOM")
    a = ap.parse_args()
    if a.close:
        return cmd_close(a.force)
    if a.open:
        return cmd_open(a.open)
    if a.open_all:
        return cmd_open_all()
    if a.check:
        return cmd_check()
    if a.set_key:
        return cmd_set_key(a.set_key)
    if a.set_id:
        if not a.email:
            print("✗ --email requis avec --set-id")
            return 1
        return cmd_set_id(a.set_id, a.email)
    return cmd_list()


if __name__ == "__main__":
    sys.exit(main())
