#!/usr/bin/env python3
"""notify_matches.py — Alerte Windows quand de NOUVELLES offres à fort fit arrivent.

Sans ça, rien ne prévient : tout est dans l'app, et si l'app est fermée les
offres fraîches dorment jusqu'à la prochaine ouverture.

Toast Windows natif via PowerShell (API Windows.UI.Notifications) — AUCUNE
dépendance à installer (win10toast/plyer/winotify ne sont pas dans le projet).

« Nouvelle » = jamais notifiée. L'état est dans _notified.json (clé
Entreprise|Poste), donc la même offre n'alerte qu'une fois, même si le pipeline
tourne tous les jours.

Run :
  python JobHunter.pyw notify_matches                  # fit >= 8, offres vivantes
  python JobHunter.pyw notify_matches --min-fit 9
  python JobHunter.pyw notify_matches --dry            # montre sans notifier ni marquer
  python JobHunter.pyw notify_matches --reset          # oublie l'historique (tout redevient nouveau)
"""

import argparse
import importlib
import json
import subprocess
import sys

from jobhunter import racine as _racine

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

HERE = _racine.scripts()
QUEUE = HERE / "apply_queue.json"
SEEN = HERE / "_notified.json"

# Un toast est ignoré si l'AppID n'est pas enregistré sur la machine ; celui du
# Terminal l'est toujours sur Win10/11.
_APPID = "Microsoft.WindowsTerminal_8wekyb3d8bbwe!App"

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
    """Titre/corps passés par variables d'environnement : les mettre dans le
    script PowerShell exposerait à l'injection via un titre d'offre contenant
    des guillemets ou $( )."""
    import os

    env = dict(os.environ, JH_TITLE=title, JH_BODY=body, JH_APPID=_APPID)
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
    q = importlib.import_module("jobhunter.stockage.file").charger(QUEUE, descriptions=False)

    seen = set()
    if SEEN.exists():
        try:
            seen = set(json.loads(SEEN.read_text(encoding="utf-8")))
        except Exception:
            pass  # historique illisible : on repart de zéro plutôt que de planter

    hits = [
        o
        for o in q
        if (o.get("fit") or 0) >= a.min_fit
        and str(o.get("link_status") or "").upper() not in ("MORT", "EXPIREE")
        and key_of(o) not in seen
    ]
    hits.sort(
        key=lambda o: (-(o.get("fit") or 0), -(o.get("fit_fin") or 0), -(o.get("ats_pct") or 0))
    )

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
    # On marque même si le toast a échoué : sinon chaque run réessaie tout le lot
    # et le jour où le toast remarche tu reçois 200 alertes d'un coup.
    seen |= {key_of(o) for o in hits}
    importlib.import_module("jobhunter.programmes.jutil").jwrite(SEEN, sorted(seen))
    print(
        f"{'notifié' if ok else 'non notifié (toast KO)'} — {len(hits)} marquée(s), historique {len(seen)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
