"""INTER-PROCESS lock through a .lock file (former section of Scripts/jutil.py).

A program that finds the file busy exits with code 3 without modifying anything; a
live lock is never broken (detail: .claude/rules/locks.md).

Decision: docs/adr/0003-file-lock-exit-code-3.md
"""

# ── Verrou INTER-PROCESSUS ────────────────────────────────────────────────────
# jwrite guarantees that a write is never cut in two. That is not enough:
# the dangerous pattern is read-all / modify / rewrite-all. Two processes
# doing that at the same time produce two valid writes, and the second
# ERASES the work of the first. That is how 4 FIR offers disappeared:
# a scan was running while scrape_desc rewrote the queue.
#
# The app does have a lock (_bg_busy), but it only holds WITHIN its process. Yet
# the scheduled task JobSearch_Daily_Scrape launches the same pipeline alongside.
#
# Hence a lock carried by a file, visible to all processes.
import atexit as _atexit
import os
import sys
import time as _time
from pathlib import Path

from jobhunter import journal as _journal

_log = _journal.journal(__name__)


_TENUS: dict[str, bool] = {}

Chemin = str | os.PathLike[str]


def _fverrou(path: Chemin) -> Path:
    return Path(str(path) + ".lock")


def _pid_vivant(pid: int | str | None, depuis: float | str | None = None) -> bool:
    """True if the process is still running. When in doubt: True (we do not break).

    A program killed by force (Stop-Process, taskkill /F, crash) does not go through
    atexit and leaves its lock behind. Without this test, one must wait for
    expiry (30 min) even though nothing holds the file any more.

    `depuis`: instant (epoch) at which the lock was set. WINDOWS RECYCLES PIDs.
    On 2026-10-02, the collection killed at 13:13 (console closed) left its lock;
    at 14:49 its PID 12720 was reassigned to a process of the Chrome extension,
    and the lock passed for held "by a live PID" — every following
    collection exited with code 3. A process born before the lock can be its
    owner; a process born AFTER cannot be.
    """
    try:
        pid = int(pid)  # type: ignore[arg-type]  # None (verrou illisible) leve TypeError, attrape
    except (TypeError, ValueError):
        return True
    if pid <= 0:
        return True
    if sys.platform == "win32":  # (and not os.name: mypy understands it under Linux)
        import ctypes

        k = ctypes.windll.kernel32
        PROCESS_QUERY_LIMITED_INFORMATION, STILL_ACTIVE = 0x1000, 259
        h = k.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h:
            # 87 = ERROR_INVALID_PARAMETER -> the PID does not exist.
            # Any other code (access denied…): we assume alive.
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
        os.kill(pid, 0)  # signal 0: does not kill, tests existence
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists but not ours
    except OSError:
        return True


def prendre_verrou(
    path: Chemin, attente: float = 180, perime: float = 1800, bavard: bool = True
) -> bool:
    """Takes the lock of `path`; reentrant for the process that already holds it.

    Args:
        path: the file to protect (the lock is a neighbouring file).
        attente: seconds to wait before giving up.
        perime: a lock older than this is considered abandoned (process
            killed without going through atexit) and broken — never a live lock.
        bavard: announce the wait on the output.

    Returns:
        True if the lock is obtained, False otherwise.
    """
    v = _fverrou(path)
    # Reentrance: a program that already holds the lock must not block
    # itself if a called function asks for it again.
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
            continue  # released in the meantime: we retry
        try:
            champs = v.read_text(encoding="utf-8").split()
            tenu_par = champs[0]
        except Exception:
            champs, tenu_par = [], ""
        try:
            pose = float(champs[1])
        except (IndexError, ValueError):
            pose = None
        # Orphan lock: the process that held it died without releasing it.
        # No point waiting for expiry, nobody touches the file any more.
        if tenu_par and not _pid_vivant(tenu_par, pose):
            if bavard:
                _log.info(f"! verrou {v.name} laisse par le PID {tenu_par}, mort — je le casse")
            try:
                v.unlink()
            except FileNotFoundError:
                pass
            continue
        # EXPIRY ONLY APPLIES TO A LOCK WITHOUT A LIVE OWNER.
        # On 2026-09-22, `linkedin_desc` read 6438 descriptions in three hours
        # under a single `transaction()`. At 17:34 it took the lock, at 18:04
        # the app's auto-scrape broke it on age — while PID 19940
        # was still running and would write the whole queue on exit. Everything
        # written in the meantime would have been erased silently.
        #
        # A long job is not an abandoned job. When the PID is
        # readable AND alive, we wait (and the caller exits with code 3 after
        # `attente`); `perime` now only decides the case where we do not know
        # who holds the lock.
        if age > perime and not tenu_par:
            if bavard:
                _log.warning(
                    f"! verrou {v.name} abandonne depuis {int(age)}s, sans proprietaire — je le casse"
                )
            try:
                v.unlink()
            except FileNotFoundError:
                pass
            continue
        if age > perime and bavard and not prevenu:
            _log.info(
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
            _log.info(f"… {v.name} tenu par le PID {qui} — j'attends (max {attente}s)")
            prevenu = True
        _time.sleep(1)


def tenu(path: Chemin) -> bool:
    """Does THIS process already hold the lock of `path`?

    `prendre_verrou` is reentrant, but `rendre_verrou` is NOT: it
    releases for good. A function that takes the lock then releases it, while
    its caller kept it for the whole duration of the program (`garder`),
    takes it away from the caller in passing — and the rest of the work runs unprotected.
    Hence this test: only release what you took yourself.

    Args:
        path: the protected file.

    Returns:
        True if this process holds the lock.
    """
    return bool(_TENUS.get(str(_fverrou(path))))


def rendre_verrou(path: Chemin) -> None:
    """Releases the lock of `path` if it is held by this process (for good).

    Args:
        path: the protected file.
    """
    v = _fverrou(path)
    if _TENUS.pop(str(v), None):
        try:
            v.unlink()
        except FileNotFoundError:
            pass


def garder(path: Chemin, attente: float = 180) -> bool:
    """To be called at the start of a program that rewrites `path` entirely.

    Takes the lock for the whole duration of the process and releases it automatically
    on exit, even on exception. Returns False if another program is already working
    on the file: the caller must then stop, not overwrite.

    Args:
        path: the file the program is going to rewrite.
        attente: seconds to wait for the lock.

    Returns:
        True if the lock is taken for the rest of the process.
    """
    if not prendre_verrou(path, attente=attente):
        _log.info(
            f"✗ {Path(path).name} est deja en cours de modification par un autre"
            f" programme. Rien n'a ete touche — relance quand il aura fini."
        )
        return False
    _atexit.register(rendre_verrou, path)
    return True
