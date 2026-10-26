"""Drag a CV onto the window: replace the profile's base CV (or, later, start a new profile).

Drag-and-drop comes from `tkinterdnd2` (the tkdnd extension, shipped for Windows, macOS
and Linux). Without it — a missing library, an unusual Tk — nothing changes: the
"Remplacer mon CV de base…" button of the CV panel does the same with a file dialog.

The pure part (which base CV it replaces, the copy and the profile update) lives in
jobhunter.base_cv, shared with the web interface.
"""

from pathlib import Path
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

from jobhunter import paths as chemins
from jobhunter import profile as _profil
from jobhunter.app.common import PY
from jobhunter.app.language import t as _t
from jobhunter.app.profiles_menu import choisir
from jobhunter.base_cv import cvs_de_base, remplacer_cv_de_base  # noqa: F401 — re-exported
from jobhunter.welcome import choisir_cv

if TYPE_CHECKING:
    from jobhunter.app._app_type import AppTypee


# ── Window part ──────────────────────────────────────────────────────────────
class DepotCvMixin:
    """A CV dropped on the window, or chosen from the CV panel."""

    def _deposer_cv(self: "AppTypee", chemins_: list[Path]) -> None:
        cv = choisir_cv(chemins_)
        if cv is None:
            messagebox.showwarning(
                "JobHunter", _t("Dépose un CV au format .docx ou .pdf."), parent=self.root
            )
            return
        if getattr(self, "_depot_vers_profil", False):  # dropped on the Profils tab
            self._nouveau_profil(cv)
            return
        i = choisir(
            self.root,
            "JobHunter",
            _t("Que faire de {cv} ?").format(cv=cv.name),
            [_t("Remplacer mon CV de base"), _t("Nouveau profil depuis ce CV")],
        )
        if i == 0:
            self._remplacer_cv(cv)
        elif i == 1:
            self._nouveau_profil(cv)

    def _choisir_cv_de_base(self: "AppTypee") -> None:
        p = filedialog.askopenfilename(
            parent=self.root,
            title=_t("Choisis ton nouveau CV de base"),
            filetypes=[("CV", "*.docx *.pdf"), ("Word", "*.docx"), ("PDF", "*.pdf")],
        )
        if p:
            self._remplacer_cv(Path(p))

    def _remplacer_cv(self: "AppTypee", cv: Path) -> None:
        try:
            noms = cvs_de_base(_profil.charger())
        except (_profil.ProfilAbsent, ValueError):
            noms = []
        ancien = noms[0] if noms else f"CV_base{cv.suffix.lower()}"
        autres = f" (+ {len(noms) - 1})" if len(noms) > 1 else ""
        if not messagebox.askyesno(
            "JobHunter",
            _t(
                "Remplacer ton CV de base ({ancien}) par {cv} ? L'ancien est gardé à côté, en .bak."
            ).format(ancien=ancien + autres, cv=cv.name),
            parent=self.root,
        ):
            return
        try:
            neuf = remplacer_cv_de_base(cv, ancien, chemins.CV_MODELES, _profil.FICHIER)
        except (OSError, ValueError) as e:
            messagebox.showerror("JobHunter", f"{type(e).__name__}: {e}", parent=self.root)
            return
        _profil.recharger()
        self._log(_t("CV de base remplacé : {nom}").format(nom=neuf) + "\n")
        if messagebox.askyesno(
            "JobHunter",
            _t("CV de base remplacé. Refaire maintenant les CV déjà préparés pour les offres ?"),
            parent=self.root,
        ):
            self.run_step(
                [PY, "-m", "jobhunter.programs.regenerate_docs", "--cv"], _t("Refaire les CV")
            )
