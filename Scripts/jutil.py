#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""jutil.py — utilitaires partagés : écriture ATOMIQUE, verrou, chemins, texte.

Un crash/kill au milieu d'une écriture ne corrompt jamais apply_queue.json.

Ce module existe aussi pour héberger les helpers que chaque programme réécrivait
de son côté. Ce n'est pas de l'esthétique : les copies DIVERGENT, et cette
divergence a déjà produit des bugs réels — une comparaison sensible à la casse
d'un côté et insensible de l'autre, une normalisation d'accents présente ici et
absente là, deux décodages `file:///` dont l'un oubliait la forme `file://`.
"""
import json, os, re, unicodedata
import time as _t
from pathlib import Path
from urllib.parse import unquote, quote


# ── Chemins ↔ URL file:/// ───────────────────────────────────────────────────
def chemin_de(u):
    """URL `file:///…` (ou chemin nu) → Path. None si vide.

    Gere `file:///` ET `file://` : trois des six copies precedentes ne
    traitaient que la premiere forme et rendaient un chemin commencant par
    « / », donc introuvable.
    """
    if not u:
        return None
    s = str(u)
    for prefixe in ("file:///", "file://"):
        if s.startswith(prefixe):
            s = s[len(prefixe):]
            break
    return Path(unquote(s))


def url_de(p):
    """Path → URL `file:///…`, séparateurs Windows convertis."""
    return "file:///" + quote(str(p).replace("\\", "/"), safe="/:")


def existe(u):
    """Le document désigné par cette URL/ce chemin est-il sur le disque ?"""
    p = chemin_de(u)
    try:
        return bool(p and p.exists())
    except OSError:      # chemin invalide pour l'OS (trop long, caracteres interdits)
        return False


# ── Normalisation de texte ───────────────────────────────────────────────────
def sans_accent(s):
    """Minuscules sans accents, via NFD.

    Remplace des tables manuelles qui oubliaient la moitie des lettres
    (« ë », « ï », « ù », « ü » n'y figuraient pas).
    """
    s = unicodedata.normalize("NFD", str(s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def cle(s):
    """Clé de comparaison : minuscules, blancs normalises. GARDE les accents.

    Volontairement distincte de `sans_accent` : cette fonction sert de cle de
    DEDUPLICATION de la queue. Lui faire ignorer les accents fusionnerait des
    offres aujourd'hui distinctes — un changement de comportement, pas un
    nettoyage. Utiliser `sans_accent(cle(s))` quand on veut les deux.
    """
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def jwrite(path, obj, _brut=False):
    """Ecriture atomique : on ecrit a cote, puis on bascule d'un seul coup.

    DEUX GARDES, chacune pour une panne observee.

    1. La QUEUE ne doit jamais reprendre les descriptions en ligne. Elles vivent
       dans descriptions.json depuis la separation ; queue_io.charger() les
       reinjecte en memoire pour le travail, et queue_io.sauver() les ressort
       avant d'ecrire. Onze programmes appellent jwrite(QUEUE, ...) en direct :
       chacun d'eux remettait les textes dans le fichier, et la queue etait
       repassee de 2,9 Mo a 15,9 Mo sans que rien ne signale la regression.
       Plutot que de compter sur onze appelants pour y penser, on redirige ici.

    2. os.replace echoue en PermissionError sous Windows quand OneDrive, un
       antivirus ou l'app tient encore un handle sur le fichier. L'echec est
       transitoire : on reessaie quelques fois avant d'abandonner.
    """
    path = Path(path)
    # _brut : queue_io a DEJA fait la separation et nous redonne la main pour
    # l'ecriture. Sans ce drapeau, sa propre ecriture repassait par la garde et
    # se rappelait a l'infini (RecursionError) des que le chemin n'etait pas le
    # fichier canonique — un fichier de test, par exemple.
    if not _brut and path.name == "apply_queue.json" and isinstance(obj, list) and any(
            isinstance(x, dict) and (x.get("description") or "").strip() for x in obj):
        import queue_io           # import tardif : queue_io importe jutil
        return queue_io.sauver(obj, path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    for essai in range(6):
        try:
            os.replace(str(tmp), str(path))
            return
        except PermissionError:
            if essai == 5:
                raise
            _t.sleep(0.5 * (essai + 1))


# ── Verrou INTER-PROCESSUS ────────────────────────────────────────────────────
# jwrite garantit qu'une ecriture n'est jamais coupee en deux. Ca ne suffit pas :
# le schema dangereux est lire-tout / modifier / reecrire-tout. Deux processus
# qui font ca en meme temps produisent deux ecritures valides, et la seconde
# EFFACE le travail de la premiere. C'est ainsi que 4 offres FIR ont disparu :
# un scan tournait pendant que scrape_desc reecrivait la queue.
#
# L'app a bien un verrou (_bg_busy), mais il ne vaut que DANS son processus. Or
# la tache planifiee JobSearch_Daily_Scrape lance le meme pipeline a cote.
#
# D'ou un verrou porte par un fichier, visible de tous les processus.
import time as _time
import atexit as _atexit

_TENUS = {}


def _fverrou(path):
    return Path(str(path) + ".lock")


def _pid_vivant(pid, depuis=None):
    """True si le processus tourne encore. En cas de doute : True (on ne casse pas).

    Un programme tue de force (Stop-Process, taskkill /F, crash) ne passe pas par
    atexit et laisse son verrou derriere lui. Sans ce test, il faut attendre
    l'expiration (30 min) alors que plus rien ne tient le fichier.

    `depuis` : instant (epoch) ou le verrou a ete pose. WINDOWS RECYCLE LES PID.
    Le 2026-10-02, la collecte tuee a 13h13 (console fermee) a laisse son verrou ;
    a 14h49 son PID 12720 a ete reattribue a un processus de l'extension Chrome,
    et le verrou passait pour tenu « par un PID vivant » — toute collecte
    suivante sortait en code 3. Un processus ne avant le verrou peut en etre le
    proprietaire ; un processus ne APRES ne peut pas l'etre.
    """
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return True
    if pid <= 0:
        return True
    if os.name == "nt":
        import ctypes
        k = ctypes.windll.kernel32
        PROCESS_QUERY_LIMITED_INFORMATION, STILL_ACTIVE = 0x1000, 259
        h = k.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h:
            # 87 = ERREUR_PARAMETRE_INVALIDE -> le PID n'existe pas.
            # Tout autre code (acces refuse…) : on suppose vivant.
            return k.GetLastError() != 87
        try:
            code = ctypes.c_ulong()
            if k.GetExitCodeProcess(h, ctypes.byref(code)) and code.value != STILL_ACTIVE:
                return False
            if depuis is not None:
                cree, fin, noyau, user = (ctypes.c_ulonglong() for _ in range(4))
                if k.GetProcessTimes(h, ctypes.byref(cree), ctypes.byref(fin),
                                     ctypes.byref(noyau), ctypes.byref(user)):
                    # FILETIME : centaines de ns depuis 1601 -> epoch Unix.
                    ne = cree.value / 1e7 - 11644473600
                    if ne > float(depuis) + 2:      # 2 s de marge d'horloge
                        return False
            return True
        finally:
            k.CloseHandle(h)
    try:
        os.kill(pid, 0)          # signal 0 : ne tue pas, teste l'existence
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True              # existe mais pas a nous
    except OSError:
        return True


def prendre_verrou(path, attente=180, perime=1800, bavard=True):
    """Prend le verrou de `path`. Rend True si obtenu, False sinon.

    attente : secondes d'attente avant d'abandonner.
    perime  : un verrou plus vieux que ca est considere abandonne (processus
              tue sans passer par atexit) et casse.
    """
    v = _fverrou(path)
    # Reentrance : un programme qui tient deja le verrou ne doit pas se bloquer
    # lui-meme si une fonction appelee le redemande.
    if _TENUS.get(str(v)):
        return True
    fin = _time.time() + attente
    prevenu = False
    while True:
        try:
            fd = os.open(str(v), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{os.getpid()} {_time.time():.0f}".encode())
            os.close(fd)
            _TENUS[str(v)] = True
            return True
        except FileExistsError:
            pass
        try:
            age = _time.time() - v.stat().st_mtime
        except FileNotFoundError:
            continue                      # libere entre-temps : on retente
        try:
            champs = v.read_text(encoding="utf-8").split()
            tenu_par = champs[0]
        except Exception:
            champs, tenu_par = [], ""
        try:
            pose = float(champs[1])
        except (IndexError, ValueError):
            pose = None
        # Verrou orphelin : le processus qui le tenait est mort sans le rendre.
        # Inutile d'attendre l'expiration, personne ne touche plus au fichier.
        if tenu_par and not _pid_vivant(tenu_par, pose):
            if bavard:
                print(f"! verrou {v.name} laisse par le PID {tenu_par}, mort — je le casse")
            try: v.unlink()
            except FileNotFoundError: pass
            continue
        # L'EXPIRATION NE S'APPLIQUE QU'A UN VERROU SANS PROPRIETAIRE VIVANT.
        # Le 2026-09-22, `linkedin_desc` lisait 6438 descriptions en trois heures
        # sous un seul `transaction()`. A 17h34 il prenait le verrou, a 18h04
        # l'auto-scrape de l'app le cassait sur l'age — alors que le PID 19940
        # tournait toujours et ecrirait la file entiere a sa sortie. Tout ce qui
        # aurait ete ecrit dans l'intervalle aurait ete efface sans bruit.
        #
        # Un travail long n'est pas un travail abandonne. Quand le PID est
        # lisible ET vivant, on attend (et l'appelant sort en code 3 au bout de
        # `attente`) ; `perime` ne tranche plus que le cas ou l'on ne sait pas
        # qui tient le verrou.
        if age > perime and not tenu_par:
            if bavard:
                print(f"! verrou {v.name} abandonne depuis {int(age)}s, sans proprietaire — je le casse")
            try: v.unlink()
            except FileNotFoundError: pass
            continue
        if age > perime and bavard and not prevenu:
            print(f"! verrou {v.name} tenu depuis {int(age)}s par le PID {tenu_par}, "
                  f"toujours vivant — j'attends au lieu de casser")
        if _time.time() >= fin:
            return False
        if bavard and not prevenu:
            try: qui = v.read_text(encoding="utf-8").split()[0]
            except Exception: qui = "?"
            print(f"… {v.name} tenu par le PID {qui} — j'attends (max {attente}s)")
            prevenu = True
        _time.sleep(1)


def verifier_motifs(espace, minimum=1):
    """Refuse de demarrer si une regex du module porte un `\\b` corrompu.

    Une frontiere de mot se corrompt de deux facons, toutes deux SILENCIEUSES —
    le motif compile, ne leve rien, et ne matche plus jamais :
      \\x08          un \\b passe dans un heredoc shell devient un backspace
      \\\\b (litteral) une « correction » du cas precedent qui echappe l'antislash

    `job_sources` avait ce controle, pas `ats_match` — et c'est `ats_match` qui
    l'avait attrape : son `_ESG_TITLE_RX` commencait par un backspace, donc le
    plafond de fit ne se levait JAMAIS pour un intitule ESG. Le scoring tournait
    depuis on ne sait quand avec sa regle principale morte. D'ou cette version
    partagee : un garde-fou recopie a la main dans chaque module finit par
    manquer la ou il sert.

    Appel type, en FIN de module (globals() doit etre complet) :

        jutil.verifier_motifs(globals(), minimum=6)

    `minimum` : nombre de motifs attendus. Si la selection cesse de rien trouver,
    le controle rassurerait sans rien verifier — on prefere qu'il crie.
    """
    import re as _re
    vus = 0
    for nom, val in list(espace.items()):
        if not isinstance(val, _re.Pattern) or not isinstance(val.pattern, str):
            continue
        vus += 1
        assert "\x08" not in val.pattern, f"{nom} : backspace au lieu de \\b"
        assert "\\\\b" not in val.pattern, f"{nom} : antislash litteral au lieu de \\b"
    assert vus >= minimum, f"verifier_motifs ne voit que {vus} motifs (>= {minimum} attendus)"
    return vus


def tenu(path):
    """CE processus tient-il deja le verrou de `path` ?

    `prendre_verrou` est reentrant, mais `rendre_verrou` ne l'est PAS : il
    libere pour de bon. Une fonction qui prend le verrou puis le rend, alors
    que son appelant le gardait pour toute la duree du programme (`garder`),
    le lui retire au passage — et la suite du travail se fait a decouvert.
    D'ou ce test : ne rendre que ce qu'on a soi-meme pris.
    """
    return bool(_TENUS.get(str(_fverrou(path))))


def rendre_verrou(path):
    v = _fverrou(path)
    if _TENUS.pop(str(v), None):
        try: v.unlink()
        except FileNotFoundError: pass


def garder(path, attente=180):
    """A appeler au debut d'un programme qui reecrit `path` en entier.

    Prend le verrou pour toute la duree du processus et le rend automatiquement
    a la sortie, meme sur exception. Rend False si un autre programme travaille
    deja sur le fichier : l'appelant doit alors s'arreter, pas ecraser.
    """
    if not prendre_verrou(path, attente=attente):
        print(f"✗ {Path(path).name} est deja en cours de modification par un autre"
              f" programme. Rien n'a ete touche — relance quand il aura fini.")
        return False
    _atexit.register(rendre_verrou, path)
    return True
