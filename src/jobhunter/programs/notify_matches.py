#!/usr/bin/env python3
"""notify_matches.py — Windows alert when NEW high-fit offers arrive.

Without it, nothing warns: everything is in the app, and if the app is closed the
fresh offers sleep until the next opening.

Native Windows toast through PowerShell (Windows.UI.Notifications API) — NO dependency
to install (win10toast/plyer/winotify are not in the project).

"New" = never notified. The state is in _notified.json (key Entreprise|Poste), so the
same offer only alerts once, even if the pipeline runs every day.

Run:
  python JobHunter.pyw notify_matches                  # fit >= 8, live offers
  python JobHunter.pyw notify_matches --min-fit 9
  python JobHunter.pyw notify_matches --dry            # shows without notifying or marking
  python JobHunter.pyw notify_matches --reset          # forgets the history (everything becomes new again)
"""

import argparse
import importlib
import json
import subprocess
import sys

from jobhunter import root as _racine
from jobhunter.scoring.ranking import rang

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]  # console : TextIOWrapper

HERE = _racine.scripts()
QUEUE = HERE / "apply_queue.json"
SEEN = HERE / "_notified.json"

# A toast is ignored if the AppID is not registered on the machine; the
# Terminal's always is on Win10/11, the fallback when JobHunter's cannot be.
_APPID = "Microsoft.WindowsTerminal_8wekyb3d8bbwe!App"


def appid():
    """JobHunter's own identity for the toasts, with its name and logo.

    Before 3.59 they came as Windows Terminal's, under its logo (the user, 2026-10-28:
    « un logo qui soit partout le même »). The identity is the windows' (Grisbix.JobHunter);
    Windows gives it a name and a logo through the Start menu shortcut that carries it
    (`jobhunter shortcut`, the installer's). Without it, the toast showed the bare
    identity: the Terminal's then.
    """
    if sys.platform != "win32":
        return _APPID
    from jobhunter.programs.shortcut import AUMID, existe

    return AUMID if existe() else _APPID


_PS = r"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType=WindowsRuntime] | Out-Null
$tpl = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$t = $tpl.GetElementsByTagName("text")
$t.Item(0).AppendChild($tpl.CreateTextNode($env:JH_TITLE)) | Out-Null
$t.Item(1).AppendChild($tpl.CreateTextNode($env:JH_BODY)) | Out-Null
$n = [Windows.UI.Notifications.ToastNotification]::new($tpl)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($env:JH_APPID).Show($n)
"""


def toast(title, body):
    """Title/body passed through environment variables: putting them into the
    PowerShell script would expose it to injection through an offer title containing
    quotes or $( )."""
    import os

    env = dict(os.environ, JH_TITLE=title, JH_BODY=body, JH_APPID=appid())
    try:
        r = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                _PS,
            ],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if r.returncode != 0:
            print(f"  ! toast échoué : {(r.stderr or '').strip()[:120]}")
            return False
        return True
    except Exception as e:
        print(f"  ! toast impossible : {type(e).__name__}")
        return False


def key_of(o):
    return f"{o.get('entreprise', '')}|{o.get('poste', '')}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-fit", type=int, default=8)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--reset", action="store_true", help="oublie l'historique des notifications")
    a = ap.parse_args()

    if a.reset:
        if SEEN.exists():
            SEEN.unlink()
        print("historique de notification remis à zéro")
        return 0

    if not QUEUE.exists():
        print("! apply_queue.json introuvable")
        return 1
    q = importlib.import_module("jobhunter.storage.queue").charger(QUEUE, descriptions=False)

    seen = set()
    if SEEN.exists():
        try:
            seen = set(json.loads(SEEN.read_text(encoding="utf-8")))
        except Exception:
            pass  # unreadable history: we start from scratch rather than crash

    hits = [
        o
        for o in q
        if (o.get("fit") or 0) >= a.min_fit
        and str(o.get("link_status") or "").upper() not in ("MORT", "EXPIREE")
        and key_of(o) not in seen
    ]
    hits.sort(key=lambda o: (-(o.get("fit") or 0), -rang(o), -(o.get("ats_pct") or 0)))

    if not hits:
        print(f"aucune NOUVELLE offre fit >= {a.min_fit} (déjà notifiées : {len(seen)})")
        return 0

    top = hits[0]
    titre = f"{len(hits)} nouvelle(s) offre(s) fit >= {a.min_fit}"
    corps = f"{top.get('entreprise', '')} — {str(top.get('poste', ''))[:60]}"
    if len(hits) > 1:
        corps += f"  (+{len(hits) - 1} autre(s))"

    print(f"=== {titre} ===")
    for o in hits[:10]:
        print(
            f"  {o.get('fit')}/10  {str(o.get('entreprise', ''))[:26]:<26} {str(o.get('poste', ''))[:44]}"
        )
    if len(hits) > 10:
        print(f"  … +{len(hits) - 10}")

    if a.dry:
        print("[dry] pas de notification, historique inchangé")
        return 0

    ok = toast(titre, corps)
    # We mark even if the toast failed: otherwise each run retries the whole batch
    # and the day the toast works again you get 200 alerts at once.
    seen |= {key_of(o) for o in hits}
    importlib.import_module("jobhunter.programs.util").jwrite(SEEN, sorted(seen))
    print(
        f"{'notifié' if ok else 'non notifié (toast KO)'} — {len(hits)} marquée(s), historique {len(seen)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
