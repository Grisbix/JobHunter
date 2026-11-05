"""DESIGN.md's « Layout » in a real headless Chromium, on a fictitious profile.

The web window answered by the real Api (tools/design_check.py, as the README
screenshots): no text against a card's edge or cut by its container, no card
stretched past its content in Réglages, and Candidatures with no application spread
over the window (the user, 2026-11-05).
"""

import importlib.util
from pathlib import Path

import pytest

OUTIL = Path(__file__).resolve().parent.parent / "tools" / "design_check.py"


@pytest.fixture(scope="module")
def outil():
    spec = importlib.util.spec_from_file_location("design_check", OUTIL)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def fenetre(outil, navigateur, tmp_path, monkeypatch):
    """A page on the fictitious folder; `candidatures=False` for an empty Candidatures."""
    pages = []

    def ouvrir(largeur=1000, candidatures=True):
        racine = tmp_path / f"dossier_{len(pages)}"
        outil.dossier_fictif(racine, candidatures=candidatures)
        monkeypatch.setenv("JOBHUNTER_RACINE", str(racine))
        monkeypatch.setenv("JOBHUNTER_LANGUE", "fr")
        monkeypatch.delenv("JOBHUNTER_PRINCIPALE", raising=False)
        # Their paths are set at import: pointed at this folder, as conftest's fixtures do.
        from jobhunter.storage import applications, queue

        monkeypatch.setattr(queue, "CHEMIN", racine / "data" / "apply_queue.json")
        monkeypatch.setattr(queue, "DESCRIPTIONS", racine / "data" / "descriptions.json")
        monkeypatch.setattr(applications, "CHEMIN", racine / "data" / "applications.json")
        pages.append(outil.ouvrir(navigateur, largeur))
        return pages[-1]

    yield ouvrir
    for p in pages:
        p.close()


@pytest.mark.parametrize("largeur", [1440, 1000])
def test_aucun_texte_contre_un_bord(outil, fenetre, largeur):
    page = fenetre(largeur)
    defauts = {}
    for ecran in outil.ECRANS:
        outil.aller(page, ecran)
        if d := outil.controler(page):
            defauts[ecran] = d
    assert not defauts, defauts


def test_reglages_cartes_a_leur_hauteur(outil, fenetre):
    """Columns of cards (.mosaique): none stretched to a taller neighbour's height."""
    page = fenetre(1440)
    outil.aller(page, "reglages")
    vides = page.evaluate("""() => [...document.querySelectorAll('.mosaique > *')].map((c) => {
      const kids = [...c.children].filter((k) => k.getClientRects().length);
      const fin = Math.max(...kids.map((k) => k.getBoundingClientRect().bottom));
      return [c.innerText.split('\\n')[0], Math.round(c.getBoundingClientRect().bottom - fin)];
    })""")
    assert vides and all(v <= 48 for _, v in vides), vides


def test_candidatures_vides_sur_toute_la_fenetre(outil, fenetre):
    page = fenetre(1000, candidatures=False)
    outil.aller(page, "candidatures")
    assert "Pas encore de candidature" in page.inner_text("#vue")
    k = page.evaluate("""() => {
      const t = document.querySelector('.tableau-kanban').getBoundingClientRect();
      const cols = [...document.querySelectorAll('.colonne-k')].map((c) => c.getBoundingClientRect());
      return { large: t.width, somme: cols.reduce((s, c) => s + c.width, 0), lignes: new Set(cols.map((c) => Math.round(c.top))).size,
               haut: Math.min(...cols.map((c) => c.height)), vue: document.getElementById('vue').clientHeight };
    }""")
    assert k["lignes"] == 1, k  # one line: wrapped, Refus sat alone across the window
    assert k["somme"] > 0.9 * k["large"], k  # the columns fill the width
    assert k["haut"] > 0.5 * k["vue"], k  # and the height


def test_l_aide_d_un_bouton_vient_au_survol_apres_un_moment(outil, fenetre):
    """`data-aide`: the user, 2026-11-05, « au bout de quelques secondes », not under the buttons."""
    page = fenetre(1000)
    outil.aller(page, "accueil")
    page.evaluate("""() => document.getElementById('vue').prepend(
      aide(bouton('Essai', '', () => {}), 'Ce que fait ce bouton.'))""")
    bulle = "(() => { const b = document.getElementById('bulle-aide'); return b && !b.hidden ? b.innerText : null; })()"
    page.hover("#vue > button")
    page.wait_for_timeout(400)
    assert page.evaluate(bulle) is None  # not at once
    page.wait_for_timeout(1200)
    assert page.evaluate(bulle) == "Ce que fait ce bouton."
    page.mouse.move(2, 2)
    assert page.evaluate(bulle) is None
