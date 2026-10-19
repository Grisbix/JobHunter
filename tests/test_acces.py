"""Régressions connexion : faux positifs et redirections, sans site distant."""

import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

from jobhunter import navigation
from jobhunter.programmes import acces


class AccesTest(unittest.TestCase):
    def test_chrome_ne_remplace_pas_le_profil_dedie(self):
        import os
        import shutil

        from jobhunter.programmes import apply_runner

        class FinDuTest(Exception):
            pass

        with tempfile.TemporaryDirectory() as t:
            racine = Path(t)
            (racine / "Google" / "Chrome" / "User Data" / "Default").mkdir(parents=True)
            profil = racine / "apply_runner_chrome"
            (profil / "Default").mkdir(parents=True)
            temoin = profil / "Default" / "session-temoin"
            temoin.write_text("session conservée", encoding="utf-8")
            with (
                patch.dict(os.environ, {"LOCALAPPDATA": t}),
                patch.object(apply_runner, "PW_USER_DIR", profil),
                patch.object(
                    sys,
                    "argv",
                    ["apply_runner.py", "--canal", "linkedin", "--chrome"],
                ),
                patch.object(shutil, "rmtree") as supprimer,
                patch.object(shutil, "copytree") as copier,
                patch.object(shutil, "copy2") as copier_fichier,
                # la file se lit par queue_io (ADR 0002) : on s'arrete la, avant tout navigateur
                patch("jobhunter.stockage.file.charger", side_effect=FinDuTest),
                redirect_stdout(io.StringIO()),
            ):
                # Arrêt avant lecture de la file et avant tout navigateur réel.
                with self.assertRaises(FinDuTest):
                    apply_runner.main()
                supprimer.assert_not_called()
                copier.assert_not_called()
                copier_fichier.assert_not_called()
            self.assertEqual(temoin.read_text(encoding="utf-8"), "session conservée")
        self.assertEqual(apply_runner.PW_USER_DIR, acces.PROFIL)

    def test_import_sans_console(self):
        spec = importlib.util.spec_from_file_location("acces_sans_console", acces.__file__)
        module = importlib.util.module_from_spec(spec)
        with patch.object(sys, "stdout", None):
            spec.loader.exec_module(module)
        self.assertTrue(callable(module.cmd_open))

    def ouvrir(self, valeurs, horloge):
        page = MagicMock()
        page.evaluate.side_effect = valeurs
        ctx = MagicMock()
        ctx.pages = [page]
        moteur = MagicMock()
        moteur.chromium.launch_persistent_context.return_value = ctx
        fabrique = MagicMock()
        fabrique.return_value.__enter__.return_value = moteur
        with (
            tempfile.TemporaryDirectory() as t,
            patch.object(acces, "PROFIL", Path(t)),
            patch.object(navigation, "get_sync_playwright", lambda _: (fabrique, "mock")),
            patch.object(acces.time, "time", side_effect=horloge),
            patch.object(acces.time, "sleep"),
            redirect_stdout(io.StringIO()),
        ):
            resultat = acces.cmd_open("indeed.com")
        ctx.close.assert_called_once()
        return resultat, page.evaluate.call_count

    def test_redirection_ne_ferme_pas_la_connexion(self):
        self.assertEqual(
            self.ouvrir([RuntimeError("Execution context was destroyed"), True], [0, 1, 2]), (0, 2)
        )

    def test_expiration_non_confirmee(self):
        self.assertEqual(self.ouvrir([False], [0, 1, 100000]), (4, 1))

    def test_signaux_session_sur_pages_locales(self):
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            navigateur = p.chromium.launch(channel="chrome", headless=True)
            try:
                page = navigateur.new_page()
                for html, attendu in [
                    ('<a>Mon compte</a><img alt="avatar">', False),
                    ('<a style="display:none">Se déconnecter</a>', False),
                    ("<button>Se déconnecter</button>", True),
                    ('<button aria-label="Sign out">Profil</button>', True),
                ]:
                    with self.subTest(html=html):
                        page.set_content(html)
                        self.assertEqual(page.evaluate(acces._SESSION_JS), attendu)
            finally:
                navigateur.close()


if __name__ == "__main__":
    unittest.main()
