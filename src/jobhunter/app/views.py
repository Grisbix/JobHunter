"""Saved views of the offer table, and the columns it shows.

A view is what makes the table say something: the column filters, the sort, the
search words and the visible columns, kept under a name (« ESG à Paris, fit ≥ 70 »)
and brought back in one click. Without it, every session started by setting the same
three filters again by hand.

The visible columns are also remembered on their own: hiding « Région » once is enough.

Everything lives in `_vues.json` of the active profile's data folder: views belong to
one search, not to the computer. Only displayed values are stored (the filters already
compare displayed values), so a view is plain JSON and survives a restart.
"""

import json
from functools import partial
from pathlib import Path
from typing import Any

from jobhunter import root as _racine

FICHIER = "_vues.json"
MODES = ("keep", "excl")


def _chemin(chemin: Path | None = None) -> Path | None:
    if chemin is not None:
        return chemin
    try:
        return _racine.scripts() / FICHIER
    except RuntimeError:
        return None


def lire(chemin: Path | None = None) -> dict[str, Any]:
    """{"vues": {name: view}, "colonnes": [...]}; empty when absent or unreadable."""
    p = _chemin(chemin)
    try:
        d = json.loads(p.read_text(encoding="utf-8")) if p else {}
    except (OSError, ValueError):
        d = {}
    if not isinstance(d, dict):
        d = {}
    vues = d.get("vues") if isinstance(d.get("vues"), dict) else {}
    cols = d.get("colonnes") if isinstance(d.get("colonnes"), list) else []
    return {"vues": vues, "colonnes": cols}


def _ecrire(d: dict[str, Any], chemin: Path | None = None) -> bool:
    p = _chemin(chemin)
    if p is None:
        return False
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)
    return True


def capturer(
    colsel: dict[str, Any], tri: tuple[Any, Any], recherche: list[str], colonnes: list[str]
) -> dict[str, Any]:
    """The table's state as a JSON-ready view."""
    filtres = {}
    for k, v in colsel.items():
        if not v:
            continue
        mode, sel = v
        filtres[k] = [mode, sorted(str(x) for x in sel)]
    return {
        "filtres": filtres,
        "tri": [tri[0], bool(tri[1])],
        "recherche": [str(m) for m in recherche],
        "colonnes": list(colonnes),
    }


def restaurer(vue: dict[str, Any], connues: list[str]) -> dict[str, Any]:
    """A saved view checked against today's columns.

    A column that no longer exists is dropped rather than failing: a view saved by an
    older version still opens, with what still makes sense.

    Returns:
        {"colsel": {...}, "tri": (key, asc), "recherche": [...], "colonnes": [...] or None}
    """
    colsel: dict[str, Any] = {}
    for k, v in (vue.get("filtres") or {}).items():
        if k in connues and isinstance(v, list) and len(v) == 2 and v[0] in MODES:
            colsel[k] = (v[0], {str(x) for x in v[1]})
    tri = vue.get("tri") or [None, False]
    cle = tri[0] if tri and tri[0] in connues else None
    return {
        "colsel": colsel,
        "tri": (cle, bool(tri[1]) if cle else False),
        "recherche": [str(m) for m in vue.get("recherche") or []],
        "colonnes": colonnes_valides(vue.get("colonnes"), connues),
    }


def colonnes_valides(cols: Any, connues: list[str]) -> list[str] | None:
    """Known columns in the table's order, the tick box always first; None if unusable."""
    if not isinstance(cols, list):
        return None
    garde = [c for c in connues if c in cols and c != "_chk"]
    return ["_chk", *garde] if garde else None


def enregistrer(nom: str, vue: dict[str, Any], chemin: Path | None = None) -> bool:
    nom = nom.strip()
    if not nom:
        return False
    d = lire(chemin)
    d["vues"][nom] = vue
    return _ecrire(d, chemin)


def supprimer(nom: str, chemin: Path | None = None) -> bool:
    d = lire(chemin)
    if d["vues"].pop(nom, None) is None:
        return False
    return _ecrire(d, chemin)


def memoriser_colonnes(cols: list[str], chemin: Path | None = None) -> bool:
    d = lire(chemin)
    d["colonnes"] = list(cols)
    return _ecrire(d, chemin)


# ── in the application ──────────────────────────────────────────────────────


def _etat(app: Any) -> dict[str, Any]:
    return capturer(
        app.colsel,
        app._sort,
        list(app._search_termes_actifs),
        list(app.tree.cget("displaycolumns")),
    )


def appliquer(app: Any, vue: dict[str, Any]) -> None:
    """Puts the table in the state of `vue` (filters, sort, search, columns)."""
    from jobhunter.app.common import COLS

    r = restaurer(vue, [c[0] for c in COLS])
    app.colsel.clear()
    app.colsel.update(r["colsel"])
    app._sort = r["tri"]
    app.e_search.delete(0, "end")
    if r["recherche"]:
        app.e_search.insert(0, " ".join(r["recherche"]))
        app._search_termes_actifs = app._search_termes()
    else:
        from jobhunter.app.common import SEARCH_HINT

        app.e_search.insert(0, SEARCH_HINT)
        app._search_termes_actifs = []
    app._montrer_colonnes(r["colonnes"] or list(app._visible_cols), memoriser=True)
    app.refresh_table()


def menu_vues(app: Any, bouton: Any) -> None:
    """The « Vues » menu: saved views, save the current one, delete, default view."""
    import tkinter as tk

    from jobhunter.app.language import t as _t

    m = tk.Menu(app.root, tearoff=0)
    vues = lire()["vues"]
    for nom in sorted(vues, key=str.lower):
        m.add_command(label=nom, command=partial(appliquer, app, vues[nom]))
    if vues:
        m.add_separator()
    m.add_command(label=_t("Enregistrer la vue actuelle…"), command=lambda: _nommer(app))
    if vues:
        sup = tk.Menu(m, tearoff=0)
        for nom in sorted(vues, key=str.lower):
            sup.add_command(label=nom, command=partial(_supprimer, app, nom))
        m.add_cascade(label=_t("Supprimer une vue"), menu=sup)
    m.add_command(
        label=_t("Vue par défaut (aucun filtre)"),
        command=lambda: appliquer(app, {"colonnes": list(app._visible_cols)}),
    )
    _deplier(m, bouton)


def _nommer(app: Any) -> None:
    import customtkinter as ctk

    from jobhunter.app.language import t as _t

    d = ctk.CTkInputDialog(
        title=_t("Enregistrer la vue"),
        text=_t("Nom de la vue (filtres, tri, recherche et colonnes actuels) :"),
    )
    nom = (d.get_input() or "").strip()
    if nom and enregistrer(nom, _etat(app)):
        app._log(_t("Vue enregistrée : {a}").format(a=nom) + "\n")


def _supprimer(app: Any, nom: str) -> None:
    from tkinter import messagebox

    from jobhunter.app.language import t as _t

    if messagebox.askyesno(_t("Supprimer une vue"), _t("Supprimer la vue « {a} » ?").format(a=nom)):
        supprimer(nom)


def menu_colonnes(app: Any, bouton: Any) -> None:
    """One tick per column; compact and full layouts in one click each."""
    import tkinter as tk

    from jobhunter.app.common import COLS
    from jobhunter.app.language import t as _t

    m = tk.Menu(app.root, tearoff=0)
    visibles = set(app.tree.cget("displaycolumns"))
    for key, lbl, _ in COLS:
        if key == "_chk":
            continue
        var = tk.BooleanVar(master=m, value=key in visibles)

        def basculer(k: str = key, v: Any = var) -> None:
            cols = set(app.tree.cget("displaycolumns"))
            cols = cols | {k} if v.get() else cols - {k}
            app._montrer_colonnes(list(cols), memoriser=True)

        m.add_checkbutton(label=_t(lbl), variable=var, command=basculer)
        m._vars = [*getattr(m, "_vars", []), var]  # type: ignore[attr-defined]  # keep the vars alive
    m.add_separator()
    m.add_command(
        label=_t("Vue compacte"),
        command=lambda: app._montrer_colonnes(list(app._visible_cols), memoriser=True),
    )
    m.add_command(
        label=_t("Toutes les colonnes"),
        command=lambda: app._montrer_colonnes([c[0] for c in COLS], memoriser=True),
    )
    _deplier(m, bouton)


def _deplier(m: Any, bouton: Any) -> None:
    try:
        m.tk_popup(bouton.winfo_rootx(), bouton.winfo_rooty() + bouton.winfo_height())
    finally:
        m.grab_release()
