"""Contrôles isolés de l'interface : aucun réseau ni écriture métier."""

import _profil_test  # noqa: F401  — les tests tournent sur le profil d'exemple
import datetime
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ["JOBHUNTER_SANS_FOND"] = "1"
os.environ.pop("JOBHUNTER_ACTION", None)
path = Path(__file__).resolve().parents[1] / "JobHunter.pyw"
loader = importlib.machinery.SourceFileLoader("jobhunter_design_test", str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
ui = importlib.util.module_from_spec(spec)
loader.exec_module(ui)


class DesignTests(unittest.TestCase):
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
        app = object.__new__(ui.App)
        offer = {"entreprise": "Test", "poste": "Analyste"}
        app.root = None
        with (
            patch.object(ui.messagebox, "askyesno", return_value=False),
            patch.object(app, "_set_statut") as statut,
            patch.object(app, "_open_offer") as ouvrir,
        ):
            app._postuler(offer)
            statut.assert_not_called()
            ouvrir.assert_not_called()
        with (
            patch.object(ui.messagebox, "askyesno", return_value=True),
            patch.object(app, "_set_statut") as statut,
            patch.object(app, "_open_offer") as ouvrir,
        ):
            app._postuler(offer)
            statut.assert_called_once_with(offer, "postulé")
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
            root = ui.ctk.CTk()
            root.withdraw()
            try:
                with patch.object(root, "state"):
                    app = ui.App(root)
                    self.assertEqual(
                        len(app.tree.cget("displaycolumns")), 9
                    )  # Pays puis Région ajoutés depuis la refonte
                    self.assertTrue(app._sidebar_on)
                    self.assertEqual(len(app._nav), 6)
                    self.assertEqual(set(app._offer_kpis), {"total", "fit", "post"})
                    self.assertEqual(app._offer_kpis["total"].cget("text"), "1")
                    self.assertEqual(app._offer_kpis["fit"].cget("text"), "1")
                    self.assertEqual(app._offer_kpis["post"].cget("text"), "0")
                    root.geometry("1080x680")
                    root.deiconify()
                    root.update_idletasks()
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
                root.destroy()


if __name__ == "__main__":
    unittest.main()
