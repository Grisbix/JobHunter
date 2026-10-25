"""Sweep of the app: every button of every panel, and every entry of "Outils", clicked.

Run on a COPY of a data root (the tool makes it): no program is started, no browser
opened, no question answered with a keyboard — each click is recorded, and any
exception of a Tk callback is an error. With --oui, the questions are answered "yes"
and the buttons of the windows that open are clicked too.

Run (needs a display; on a server: xvfb-run -a python tools/sweep_app.py …):
  python tools/sweep_app.py --racine <dossier de données>          # its copy, French
  python tools/sweep_app.py --racine <dossier> --oui --langue en
Exit code 1 if a click raised an error; the log lists every click.
"""

import argparse
import io
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
import webbrowser
from pathlib import Path

ICI = Path(__file__).resolve().parent.parent
SAUTER = ("Arrêter", "Stopper", "Quitter", "Stop", "Quit")
PANNEAUX = [
    "profil",
    "offres",
    "recherche",
    "cv",
    "entreprises",
    "sites",
    "stats",
    "acces",
    "parametres",
]


def balayer(app, journal: str, oui: bool) -> None:
    """Called inside the app (JOBHUNTER_ACTION), `app` being the window."""
    import tkinter
    from tkinter import filedialog, messagebox, simpledialog

    log = open(journal, "w", encoding="utf-8")  # noqa: SIM115 : closed at the end

    def dire(*a):
        print(*a, file=log, flush=True)

    class FauxProc:  # no program is started: the command is written down
        def __init__(self, cmd, *a, **k):
            dire("   lance", " ".join(map(str, cmd))[-140:] if isinstance(cmd, list) else cmd)
            self.stdout, self.stderr = io.StringIO(""), io.StringIO("")
            self.returncode, self.pid = 0, 1

        def poll(self):
            return 0

        def wait(self, *a, **k):
            return 0

        def communicate(self, *a, **k):
            return "", ""

        def kill(self):
            pass

        terminate = kill

    subprocess.Popen = FauxProc
    webbrowser.open = lambda *a, **k: dire("   navigateur", a[0] if a else "")
    for n in ("showinfo", "showwarning", "showerror"):
        setattr(messagebox, n, lambda *a, _n=n, **k: dire(f"   {_n}", str(a[1:2])[:160]))
    for n in ("askyesno", "askokcancel", "askyesnocancel", "askquestion"):
        setattr(messagebox, n, lambda *a, **k: oui)
    simpledialog.askstring = lambda *a, **k: None
    simpledialog.askinteger = lambda *a, **k: None
    for n in ("askopenfilename", "askdirectory", "asksaveasfilename"):
        setattr(filedialog, n, lambda *a, **k: "")
    tkinter.Misc.wait_window = lambda self, *a: None

    erreurs = []

    def erreur(*a):
        t = "".join(traceback.format_exception(*a))
        erreurs.append(t)
        dire("!! ERREUR", t[-900:])

    app.root.report_callback_exception = erreur
    nav = set(app._nav.values())

    def boutons(w):
        out = []
        for c in w.winfo_children():
            if c in nav or (isinstance(c, tkinter.Toplevel) and w is app.root):
                continue
            try:
                if not c.winfo_ismapped():  # another panel, hidden
                    continue
            except Exception:
                continue
            n = c.__class__.__name__
            if n == "CTkSegmentedButton" and "English" in (c.cget("values") or []):
                continue  # the language: it restarts the app
            if n in (
                "CTkButton",
                "Button",
                "CTkSegmentedButton",
                "CTkSwitch",
                "CTkCheckBox",
                "CTkRadioButton",
            ):
                out.append(c)
            out += boutons(c)
        return out

    def texte(b):
        try:
            return str(b.cget("text"))
        except Exception:
            return "?"

    profond = [False]

    def fermer(avant):
        for t in app.root.winfo_children():
            if isinstance(t, tkinter.Toplevel) and t not in avant:
                dire("   fenêtre", t.title())
                if oui and not profond[0]:
                    profond[0] = True
                    for b in boutons(t):
                        if b.winfo_exists():
                            cliquer(b, f"  dans {t.title()[:20]}")
                    profond[0] = False
                try:
                    t.destroy()
                except Exception:
                    pass

    def cliquer(b, ou):
        tx = texte(b)
        if any(s in tx for s in SAUTER):
            return
        avant = set(app.root.winfo_children())
        dire(f" [{ou}] {tx[:50]!r}")
        try:
            if b.__class__.__name__ == "CTkSegmentedButton":
                for v in b.cget("values"):
                    b.set(v)
                    if b.cget("command"):
                        b.cget("command")(v)
            elif hasattr(b, "toggle"):  # CTkSwitch, CTkCheckBox: on, then back
                b.toggle()
                app.root.update()
                b.toggle()
            else:
                b.invoke()
            app.root.update()
        except Exception:
            erreur(*sys.exc_info())
        fermer(avant)

    def menu(m, chemin=""):
        fin = m.index("end")
        for i in range(0 if fin is None else fin + 1):
            if m.type(i) == "cascade":
                menu(
                    m.nametowidget(m.entrycget(i, "menu")), f"{chemin}{m.entrycget(i, 'label')} > "
                )
            elif m.type(i) == "command":
                avant = set(app.root.winfo_children())
                dire(f" [Outils] {chemin}{m.entrycget(i, 'label')}")
                try:
                    m.invoke(i)
                    app.root.update()
                except Exception:
                    erreur(*sys.exc_info())
                fermer(avant)

    def panneau(i):
        if i == len(PANNEAUX):
            try:
                menu(app._menu_reglages())
            except Exception:
                erreur(*sys.exc_info())
            dire(f"FIN : {len(erreurs)} erreur(s)")
            log.close()
            app.root.destroy()
            return
        cle = PANNEAUX[i]
        try:
            app._nav[cle].invoke()
            app.root.update()
            vus = boutons(app.root)
            dire(f"== {cle} : {len(vus)} boutons")
            for b in vus:
                try:
                    if b.winfo_exists():
                        cliquer(b, cle)
                        app._nav[cle].invoke()  # back to the panel after each click
                        app.root.update()
                except Exception:
                    erreur(*sys.exc_info())
        except Exception:
            erreur(*sys.exc_info())
        app.root.after(300, lambda: panneau(i + 1))

    app.root.state("normal")
    app.root.geometry("1320x840+0+0")
    app.root.after(1000, lambda: panneau(0))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--racine", required=True, help="dossier de données (il est copié)")
    ap.add_argument("--oui", action="store_true", help="répondre oui, cliquer dans les fenêtres")
    ap.add_argument("--langue", default="fr")
    ap.add_argument("--journal", default="", help="fichier du journal (défaut : dans la copie)")
    a = ap.parse_args()
    copie = Path(tempfile.mkdtemp(prefix="sweep_app_")) / "racine"
    shutil.copytree(a.racine, copie, ignore=shutil.ignore_patterns("profiles", "_backups"))
    journal = a.journal or str(copie.parent / "clics.log")
    action = (
        f"import sys; sys.path.insert(0, {str(ICI / 'tools')!r}); import sweep_app; "
        f"sweep_app.balayer(app, {journal!r}, {a.oui!r})"
    )
    env = {k: v for k, v in os.environ.items() if k != "PROFIL_JOBHUNTER"}
    env.update(
        JOBHUNTER_RACINE=str(copie),
        JOBHUNTER_PRINCIPALE=str(copie),
        JOBHUNTER_SANS_FOND="1",
        JOBHUNTER_ACTION=action,
        JOBHUNTER_LANGUE=a.langue,
        PYTHONIOENCODING="utf-8",
    )
    r = subprocess.run([sys.executable, str(ICI / "JobHunter.pyw")], env=env, timeout=3600)
    texte = Path(journal).read_text(encoding="utf-8") if Path(journal).exists() else ""
    clics = texte.count("\n [")
    fin = [l for l in texte.splitlines() if l.startswith("FIN")]
    print(
        f"{clics} clic(s) · {fin[0] if fin else 'pas de fin : la fenêtre a quitté avant'}"
        f" · journal : {journal}"
    )
    for bloc in texte.split("!! ERREUR")[1:]:
        print("!! ERREUR", bloc.strip()[-600:], "\n")
    return 0 if r.returncode == 0 and fin and fin[0].startswith("FIN : 0 ") else 1


if __name__ == "__main__":
    sys.exit(main())
