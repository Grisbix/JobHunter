"""Verrou INTER-PROCESSUS par fichier .lock (ancienne section de Scripts/jutil.py).

Un programme qui trouve le fichier occupe sort en code 3 sans rien modifier ; un
verrou vivant ne se casse jamais (detail : .claude/rules/verrous.md).
"""

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
import atexit as _atexit
import os
import sys
import time as _time
from pathlib import Path

_TENUS: dict[str, bool] = {}

Chemin = str | os.PathLike[str]


def _fverrou(path: Chemin) -> Path:
    return Path(str(path) + ".lock")


def _pid_vivant(pid: int | str | None, depuis: float | str | None = None) -> bool:
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
        pid = int(pid)  # type: ignore[arg-type]  # None (verrou illisible) leve TypeError, attrape
    except (TypeError, ValueError):
        return True
    if pid <= 0:
        return True
    if sys.platform == "win32":  # (et non os.name : mypy le comprend sous Linux)
        import ctypes

        k = ctypes.windll.kernel32
        PROCESS_QUERY_LIMITED_INFORMATION, STILL_ACTIVE = 0x1000, 259
        h = k.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h:
            # 87 = ERREUR_PARAMETRE_INVALIDE -> le PID n'existe pas.
            # Tout autre code (acces refuse…) : on suppose vivant.
            return bool(k.GetLastError() != 87)
        try:
            code = ctypes.c_ulong()
            if k.GetExitCodeProcess(h, ctypes.byref(code)) and code.value != STILL_ACTIVE:
                return False
            if depuis is not None:
                cree, fin, noyau, user = (ctypes.c_ulonglong() for _ in range(4))
                if k.GetProcessTimes(
                    h,
                    ctypes.byref(cree),
                    ctypes.byref(fin),
                    ctypes.byref(noyau),
                    ctypes.byref(user),
                ):
                    # FILETIME : centaines de ns depuis 1601 -> epoch Unix.
                    ne = cree.value / 1e7 - 11644473600
                    if ne > float(depuis) + 2:  # 2 s de marge d'horloge
                        return False
            return True
        finally:
            k.CloseHandle(h)
    try:
        os.kill(pid, 0)  # signal 0 : ne tue pas, teste l'existence
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # existe mais pas a nous
    except OSError:
        return True


def prendre_verrou(
    path: Chemin, attente: float = 180, perime: float = 1800, bavard: bool = True
) -> bool:
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
            continue  # libere entre-temps : on retente
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
            try:
                v.unlink()
            except FileNotFoundError:
                pass
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
                print(
                    f"! verrou {v.name} abandonne depuis {int(age)}s, sans proprietaire — je le casse"
                )
            try:
                v.unlink()
            except FileNotFoundError:
                pass
            continue
        if age > perime and bavard and not prevenu:
            print(
                f"! verrou {v.name} tenu depuis {int(age)}s par le PID {tenu_par}, "
                f"toujours vivant — j'attends au lieu de casser"
            )
        if _time.time() >= fin:
            return False
        if bavard and not prevenu:
            try:
                qui = v.read_text(encoding="utf-8").split()[0]
            except Exception:
                qui = "?"
            print(f"… {v.name} tenu par le PID {qui} — j'attends (max {attente}s)")
            prevenu = True
        _time.sleep(1)


def tenu(path: Chemin) -> bool:
    """CE processus tient-il deja le verrou de `path` ?

    `prendre_verrou` est reentrant, mais `rendre_verrou` ne l'est PAS : il
    libere pour de bon. Une fonction qui prend le verrou puis le rend, alors
    que son appelant le gardait pour toute la duree du programme (`garder`),
    le lui retire au passage — et la suite du travail se fait a decouvert.
    D'ou ce test : ne rendre que ce qu'on a soi-meme pris.
    """
    return bool(_TENUS.get(str(_fverrou(path))))


def rendre_verrou(path: Chemin) -> None:
    v = _fverrou(path)
    if _TENUS.pop(str(v), None):
        try:
            v.unlink()
        except FileNotFoundError:
            pass


def garder(path: Chemin, attente: float = 180) -> bool:
    """A appeler au debut d'un programme qui reecrit `path` en entier.

    Prend le verrou pour toute la duree du processus et le rend automatiquement
    a la sortie, meme sur exception. Rend False si un autre programme travaille
    deja sur le fichier : l'appelant doit alors s'arreter, pas ecraser.
    """
    if not prendre_verrou(path, attente=attente):
        print(
            f"✗ {Path(path).name} est deja en cours de modification par un autre"
            f" programme. Rien n'a ete touche — relance quand il aura fini."
        )
        return False
    _atexit.register(rendre_verrou, path)
    return True
