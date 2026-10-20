#!/usr/bin/env python3
"""acces.py — Manages ACCESS to sites, WITHOUT ever storing a password.

WHY NO PASSWORDS HERE
A file of plain-text passwords next to the code is the worst possible place: synced by
OneDrive, readable by any program on the PC, and one day committed by mistake. Chrome
already has a password manager encrypted by the system — IT is the one that must fill
the forms.

HOW THE PROGRAMS "OPEN EVERYTHING"
acces.py and apply_runner share a dedicated, persistent Chrome profile.
You log in by hand through --open; apply_runner then reuses that profile, with or
without --chrome, without replacing it with your everyday Chrome.
The other collectors have their own profile options.
No password goes through the code.

WHAT THIS FILE KEEPS
  - the login URL of each site
  - the identifier (email) used — not the password
  - the session state seen at the last check
  - the API KEYS (non-password secrets: France Travail...), entered masked and
    never displayed

Run:
  python JobHunter.pyw acces --list                    # state of the accesses
  python JobHunter.pyw acces --open linkedin.com       # opens the login page in YOUR Chrome
  python JobHunter.pyw acces --check                   # tests which sessions are still active
  python JobHunter.pyw acces --set-id linkedin.com --email me@x.fr
  python JobHunter.pyw acces --set-key francetravail   # masked entry of an API key
"""

import argparse
import datetime
import getpass
import importlib
import json
import sys
import time
from pathlib import Path

from jobhunter import root as _racine

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

HERE = _racine.scripts()
COMPTES = HERE / "comptes.json"
KEYS = HERE / "api_keys.json"  # gitignore: contains secrets

# SAME profile as apply_runner: the sessions opened here are the ones the
# scripts will find. Pointing to Chrome's "User Data" root does NOT
# work — Chrome starts another instance and drops Playwright (TargetClosedError).
# A dedicated profile also avoids having to close the everyday Chrome.
import os as _os

PROFIL = Path(_os.environ.get("LOCALAPPDATA", str(Path.home()))) / "apply_runner_chrome"

# Sites where a logged-in session changes what can be done.
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
    importlib.import_module("jobhunter.programs.util").jwrite(p, obj)


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
    from jobhunter import api_keys as cles_api

    print("\nCLES DES API DE COLLECTE — valeurs jamais affichees :")
    for nom, cle in cles_api.CLES.items():
        etat = "✓ posee" if cles_api.presente(HERE, nom) else "✗ absente"
        print(f"  {cle.libelle:<16}{cle.fichier:<22}{etat}")
    if k:
        print(f"  ({KEYS.name} : {', '.join(sorted(k))} — lu par aucune source de collecte)")
    print("\nLes MOTS DE PASSE restent dans le gestionnaire de Chrome — jamais ici.")
    return 0


# Maximum wait for a manual login, in minutes.
ATTENTE_MIN = 15


def _procs_profil():
    """(pid, ppid) of the Chrome processes started on THE dedicated profile, and only them.

    We filter on --user-data-dir in the command line: killing chrome.exe en masse
    would close the user's personal browser, with its tabs and its forms in
    progress. Never.
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
    """The ROOT Chrome processes of the profile (parent outside Chrome).

    Only the root owns a window. taskkill without /F sends WM_CLOSE, which only
    reaches processes with a window: targeting the children (renderers, GPU) closes
    nothing at all. It is the root that must be asked to close, and it takes its
    children with it when it stops cleanly — hence writing its cookies to disk.
    """
    procs = _procs_profil()
    connus = {pid for pid, _ in procs}
    return [pid for pid, ppid in procs if ppid not in connus]


def cmd_close(force=False):
    """Closes the Chrome processes left open on the dedicated profile.

    Used to unlock the profile: as long as a Chrome holds it, --check cannot read it
    and the cookies are not guaranteed to be written to disk.
    We first send a NORMAL close (taskkill without /F closes the windows cleanly,
    Chrome then flushes its caches). /F only as a last resort, and only with --force.
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
    """Opens the login page in YOUR Chrome. You log in by hand;
    Chrome remembers, and --chrome will reuse the session."""
    url = SITES_CONNEXION.get(host)
    if not url:
        print(f"✗ site inconnu. Connus : {', '.join(SITES_CONNEXION)}")
        return 1
    # Opening in the DEFAULT browser would store the session in the
    # everyday profile — invisible to the scripts. So we open the
    # dedicated profile, the one that apply_runner and --check use.
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
        # ACTIVE wait: we re-read the session state every 2 s and close
        # as soon as the login is done. No more need for a human to close the
        # window, nor for a usable stdin (input() raises EOFError under an agent,
        # and isatty() lies: it returns True while stdin is already closed).
        print(f"  Attente de la connexion (jusqu a {ATTENTE_MIN} min)...")
        fin = time.time() + ATTENTE_MIN * 60
        connecte = False
        while time.time() < fin:
            if not ctx.pages:  # window closed by hand = done
                break
            try:
                if ctx.pages[0].evaluate(_SESSION_JS):
                    connecte = True
                    break
                ctx.pages[0].wait_for_timeout(2000)
            except Exception:
                # An OAuth redirect temporarily destroys the JS context.
                # Wait for the next round, without closing the login in progress.
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
    """Opens each site with the real Chrome profile and looks whether we are logged in.
    Types NOTHING: read-only check of the session state."""
    # A Chrome still open HOLDS the profile: launch_persistent_context fails
    # or starts on an incomplete profile. We release it first, cleanly.
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
            # NO --disable-blink-features here: this flag triggers the banner
            # "Vous utilisez un indicateur de ligne de commande non pris en
            # charge". This script only READS a session state, it does not
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
            # Tell the two causes apart: the previous message announced
            # "profil verrouillé" even on a simple timeout.
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
                # The consent banner hides the page and skews analyze().
                # COOKIE_JS looks for "Tout refuser" first (OneTrust, Didomi,
                # Axeptio, tarteaucitron): the most privacy-respecting option.
                try:
                    dismiss_cookies(page)
                    page.wait_for_timeout(700)
                except Exception:
                    pass
                a = analyze(page)
                kind = str(a.get("kind") or "?")
                # A login OR sign-up form = not logged in.
                # ("register" was counted as logged in: LinkedIn and Indeed
                # came out "connecté" while they displayed a sign-up.)
                if a.get("blocked") or a.get("captcha"):
                    etat = "bloque"
                elif kind in ("login", "register"):
                    etat = "deconnecte"
                else:
                    # The absence of a form proves nothing: we look for a sign
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
    """Opens EACH login page in its own tab, on the dedicated profile,
    and leaves the browser open so that you log in site by site.

    No input() here: run in the background, stdin is closed and an input() would
    cause an EOFError that would immediately close the browser again. So we wait for
    YOU to close the tabs — the script ends when none are left, and Chrome has then
    written the sessions to disk.
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
                # Sets aside the cookie banner (refusal first) so that you land
                # directly on the login form.
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
            while ctx.pages:  # holds as long as a tab stays open
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
    """MASKED entry of the key of a collection API, in the file the source reads.

    Before 2.12, it went into api_keys.json, which no source reads (cles_api).
    Value never displayed nor logged; an empty field keeps the value in place.
    """
    from jobhunter import api_keys as cles_api

    cle = cles_api.CLES.get(nom)
    if cle is None:
        print(f"✗ source inconnue : {nom} — au choix : {', '.join(cles_api.CLES)}")
        return 1
    print(f"Cle {cle.libelle} → {cle.fichier} — saisie masquee, valeur jamais reaffichee.")
    print(f"  (a creer sur {cle.obtenir} ; champ vide = garder la valeur en place)")
    valeurs = {}
    for champ in cle.champs:
        if champ in cle.secrets:
            valeurs[champ] = getpass.getpass(f"  {champ} : ").strip()
        else:
            valeurs[champ] = input(f"  {champ} : ").strip()
    try:
        chemin = cles_api.enregistrer(HERE, nom, valeurs)
    except (OSError, ValueError) as e:
        print(f"✗ {e}")
        return 1
    print(f"✓ {cle.libelle} enregistre dans {chemin.name} — fichier ignore par git")
    return 0


def get_key(nom):
    """Programmatic read of a key (for the other scripts)."""
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
    ap.add_argument("--set-key", metavar="SOURCE", help="francetravail, adzuna ou jooble")
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
