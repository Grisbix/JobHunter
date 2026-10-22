"""Contrôles isolés de l'interface : aucun réseau ni écriture métier."""

import datetime
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pytest

os.environ["JOBHUNTER_SANS_FOND"] = "1"
os.environ.pop("JOBHUNTER_ACTION", None)
# The app lives in jobhunter.app since phase 3.7; JobHunter.pyw is only the launcher.
import jobhunter.app as ui  # noqa: E402  (after the environment variables)


class DesignTests(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def _racine(self, racine_tk):
        # The session's Tk root (conftest): a second root in the same
        # process makes Tcl initialisation fail intermittently.
        self.racine = racine_tk

    def test_sessions(self):
        today = datetime.date(2026, 10, 5)
        for verification in ("2026-08-31", None, "invalide", "2026-11-01"):
            with self.subTest(verification=verification):
                self.assertEqual(
                    ui._session_presentation("connecte", verification, today),
                    ("À revérifier", "ancien"),
                )
        self.assertEqual(
            ui._session_presentation("connecte", "2026-10-05", today), ("Connecté", "ok")
        )
        self.assertEqual(
            ui._session_presentation("deconnecte", "2026-10-04", today), ("Déconnecté", "ko")
        )

    def test_envoi_explicite(self):
        """Nothing is written without an explicit "yes"; the yes declares the sending (ADR 0009)."""
        app = object.__new__(ui.App)
        offer = {"entreprise": "Test", "poste": "Analyste"}
        app.root = None
        with (
            patch.object(ui.messagebox, "askyesno", return_value=False),
            patch("jobhunter.app.actions.suivi_io.declarer_envoi") as declarer,
            patch.object(app, "_open_offer") as ouvrir,
        ):
            app._postuler(offer)
            declarer.assert_not_called()
            ouvrir.assert_not_called()
            ouvrir.assert_not_called()

    def test_panneaux_et_colonnes(self):
        offer = {
            "entreprise": "Test",
            "poste": "Analyste " + "durable " * 12,
            "fit": 9,
            "contrat": "CDI",
            "description": "Description fictive",
            "url": "https://example.invalid/offre",
        }
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(ui.queue_io, "charger", return_value=[offer]),
            patch.object(ui.suivi_io, "charger", return_value={}),
            patch.object(ui, "SUIVI", Path(directory) / "suivi.json"),
            patch.object(ui, "COMPTES", Path(directory) / "comptes.json"),
            patch.object(ui, "PROFILE", Path(directory) / "profil.json"),
        ):
            root = self.racine
            root.withdraw()
            try:
                with patch.object(root, "state"):
                    app = ui.App(root)
                    # ⚑ added, Country and Region one click away (3.15); Publiée, Vérifiée (3.17)
                    self.assertEqual(len(app.tree.cget("displaycolumns")), 10)
                    self.assertTrue(app._sidebar_on)
                    app._toggle_sidebar(
                        garder=False
                    )  # « Réduire le menu »: the table takes the width
                    self.assertFalse(app._sidebar_on)
                    self.assertEqual(app.b_menu.cget("text"), "☰ Menu")
                    app._toggle_sidebar(garder=False)
                    self.assertTrue(app._sidebar_on)
                    self.assertEqual(len(app._nav), 7)  # + "Ma recherche" (3.9)
                    self.assertEqual(set(app._offer_kpis), {"total", "fit", "post"})
                    self.assertEqual(app._offer_kpis["total"].cget("text"), "1")
                    self.assertEqual(app._offer_kpis["fit"].cget("text"), "1")
                    self.assertEqual(app._offer_kpis["post"].cget("text"), "0")
                    root.geometry("1080x680")
                    root.deiconify()
                    # update() and not update_idletasks(): displaying a window
                    # (Map event) is not an "idle" task. Locally the window
                    # was often already displayed; on the CI machine, never.
                    root.update()
                    self.assertTrue(app._offer_split.winfo_ismapped())
                    self.assertTrue(app.sidebar.winfo_ismapped())
                    root.withdraw()
                    for sequence in ("<Control-a>", "<Control-z>", "<Control-Return>"):
                        self.assertTrue(app.tree.bind(sequence))
                        self.assertFalse(root.bind_all(sequence))
                    app._toggle_columns()
                    self.assertEqual(len(app.tree.cget("displaycolumns")), len(ui.COLS))
                    self.assertEqual(
                        app._urlcol, "#" + str([c[0] for c in ui.COLS].index("_url") + 1)
                    )
                    app._toggle_columns()
                    self.assertIsNone(app._urlcol)
                    self.assertEqual(len(app._row_vals(offer)), len(ui.COLS))
                    app.colsel = {"poste": ("keep", {app._cell(offer, "poste")})}
                    app.refresh_table()
                    self.assertEqual(len(app.tree.get_children()), 1)
                    app._toggle_maint()
                    app._toggle_maint()
                    app._toggle_suivi()
                    app._toggle_suivi()
                    for panel in (
                        app._stats_panel,
                        app._acces_panel,
                        app._cv_viewer,
                        app._companies_panel,
                        app._sources_panel,
                        app._show_dash,
                    ):
                        panel()
                    self.assertEqual(len(app._panels["stats"]._cards), 10)
                    self.assertFalse((Path(directory) / "suivi.json").exists())
            finally:
                for w in root.winfo_children():
                    w.destroy()
                root.deiconify()
                root.attributes("-alpha", 0.0)


if __name__ == "__main__":
    unittest.main()
