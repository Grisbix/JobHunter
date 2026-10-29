"""JobHunter's logo, drawn from one place (3.66).

A target with a check: the offer that fits. Indigo and coral. This script writes
every form of it, so that none is redrawn by hand:

- ``docs/brand/``: the SVGs — the tile (the app icon), the mark alone for light
  and dark backgrounds and in one colour, and the name under or beside the mark;
- ``src/jobhunter/app/assets/jobhunter.png`` and ``.ico``, ``web/static/logo.png``,
  and ``docs/brand/store-300.png`` (the Store listing's logo).

The name is set in Segoe UI Bold and written as outlines, so every SVG looks the
same without the font. Needs Pillow and fontTools (not project dependencies:
the outputs are committed). Run: ``python tools/brand.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
BRAND = RACINE / "docs" / "brand"
ASSETS = RACINE / "src" / "jobhunter" / "app" / "assets"
STATIC = RACINE / "src" / "jobhunter" / "web" / "static"
POLICE = Path("C:/Windows/Fonts/segoeuib.ttf")

INDIGO = "#4f46e5"
CORAIL = "#fb7185"
ENCRE = "#1e1b4b"
BLANC = "#ffffff"

# Geometry on a 96 × 96 grid. The tile's mark is smaller than the free one:
# the tile's own edge already frames it.
TUILE = {"r": (28, 13), "trait": 7, "coche": ((37, 49), (45, 57), (60, 40)), "epais": 8}
LIBRE = {"r": (36, 17), "trait": 9, "coche": ((35, 49), (45, 59), (64, 37)), "epais": 10}
ARRONDI = 22
ICO = (16, 24, 32, 48, 64, 128, 256)


def _marque(g: dict, anneau: str, coche: str) -> str:
    (x0, y0), (x1, y1), (x2, y2) = g["coche"]
    cercles = "".join(
        f'<circle cx="48" cy="48" r="{r}" fill="none" stroke="{anneau}" stroke-width="{g["trait"]}"/>'
        for r in g["r"]
    )
    return (
        f'{cercles}<path d="M{x0} {y0}L{x1} {y1}L{x2} {y2}" fill="none" stroke="{coche}" '
        f'stroke-width="{g["epais"]}" stroke-linecap="round" stroke-linejoin="round"/>'
    )


def _svg(largeur: float, hauteur: float, corps: str, titre: str = "JobHunter") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largeur:g} {hauteur:g}" '
        f'role="img"><title>{titre}</title>{corps}</svg>\n'
    )


def tuile() -> str:
    fond = f'<rect width="96" height="96" rx="{ARRONDI}" fill="{INDIGO}"/>'
    return _svg(96, 96, fond + _marque(TUILE, BLANC, CORAIL))


def nom(taille: float) -> tuple[str, float]:
    """« JobHunter » as one SVG path at `taille` px, baseline at y = 0; and its width."""
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont

    police = TTFont(POLICE)
    glyphes = police.getGlyphSet()
    cmap = police.getBestCmap()
    echelle = taille / police["head"].unitsPerEm
    stylo = SVGPathPen(glyphes)
    x = 0.0
    for lettre in "JobHunter":
        g = cmap[ord(lettre)]
        glyphes[g].draw(TransformPen(stylo, (echelle, 0, 0, -echelle, x, 0)))
        x += glyphes[g].width * echelle
    return stylo.getCommands(), x


def _arrondir(chemin: str) -> str:
    """Two decimals are plenty for a logo, and halve the file."""
    import re

    return re.sub(
        r"-?\d+\.\d+", lambda m: f"{float(m.group()):.2f}".rstrip("0").rstrip("."), chemin
    )


def empile(anneau: str, texte: str) -> str:
    chemin, large = nom(26)
    corps = f'<g transform="translate(27 4)">{_marque(LIBRE, anneau, CORAIL)}</g>'
    corps += f'<path transform="translate({(150 - large) / 2:.2f} 134)" fill="{texte}" d="{_arrondir(chemin)}"/>'
    return _svg(150, 144, corps)


def en_ligne(anneau: str, texte: str) -> str:
    chemin, large = nom(26)
    corps = f'<g transform="translate(2 4) scale(.5)">{_marque(LIBRE, anneau, CORAIL)}</g>'
    corps += f'<path transform="translate(60 37)" fill="{texte}" d="{_arrondir(chemin)}"/>'
    return _svg(60 + large + 4, 56, corps)


def mono() -> str:
    """One colour (the text's): the rings are cut around the check, else they merge."""
    (x0, y0), (x1, y1), (x2, y2) = LIBRE["coche"]
    coche = f"M{x0} {y0}L{x1} {y1}L{x2} {y2}"
    masque = (
        '<mask id="jh-coche"><rect width="96" height="96" fill="#fff"/>'
        f'<path d="{coche}" fill="none" stroke="#000" stroke-width="{LIBRE["epais"] + 8}" '
        'stroke-linecap="round" stroke-linejoin="round"/></mask>'
    )
    anneaux = "".join(
        f'<circle cx="48" cy="48" r="{r}" fill="none" stroke="currentColor" stroke-width="{LIBRE["trait"]}"/>'
        for r in LIBRE["r"]
    )
    trait = (
        f'<path d="{coche}" fill="none" stroke="currentColor" stroke-width="{LIBRE["epais"]}" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
    )
    return _svg(96, 96, f'{masque}<g mask="url(#jh-coche)">{anneaux}</g>{trait}')


def svgs() -> dict[str, str]:
    seul = lambda anneau, coche: _svg(96, 96, _marque(LIBRE, anneau, coche))  # noqa: E731
    return {
        "jobhunter-tile.svg": tuile(),
        "jobhunter-mark-light.svg": seul(INDIGO, CORAIL),
        "jobhunter-mark-dark.svg": seul(BLANC, CORAIL),
        "jobhunter-mark-mono.svg": mono(),
        "jobhunter-stacked-light.svg": empile(INDIGO, ENCRE),
        "jobhunter-stacked-dark.svg": empile(BLANC, BLANC),
        "jobhunter-inline-light.svg": en_ligne(INDIGO, ENCRE),
        "jobhunter-inline-dark.svg": en_ligne(BLANC, BLANC),
    }


def image_tuile(cote: int):
    """The tile drawn at `cote` px: drawn 8 times larger, then reduced (smooth edges)."""
    from PIL import Image, ImageDraw

    k = cote * 8 / 96
    im = Image.new("RGBA", (cote * 8, cote * 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, cote * 8 - 1, cote * 8 - 1), radius=ARRONDI * k, fill=INDIGO)
    trait = TUILE["trait"] * k
    for r in TUILE["r"]:
        r *= k
        c = 48 * k
        d.ellipse(
            (c - r - trait / 2, c - r - trait / 2, c + r + trait / 2, c + r + trait / 2),
            outline=BLANC,
            width=round(trait),
        )
    points = [(x * k, y * k) for x, y in TUILE["coche"]]
    epais = TUILE["epais"] * k
    d.line(points, fill=CORAIL, width=round(epais), joint="curve")
    for x, y in (points[0], points[-1]):
        d.ellipse((x - epais / 2, y - epais / 2, x + epais / 2, y + epais / 2), fill=CORAIL)
    return im.resize((cote, cote), Image.Resampling.LANCZOS)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    BRAND.mkdir(parents=True, exist_ok=True)
    for fichier, contenu in svgs().items():
        (BRAND / fichier).write_bytes(contenu.encode("utf-8"))
    image_tuile(256).save(ASSETS / "jobhunter.png", optimize=True)
    # The web page's logo is the same file (3.58: one logo).
    (STATIC / "logo.png").write_bytes((ASSETS / "jobhunter.png").read_bytes())
    image_tuile(300).save(BRAND / "store-300.png", optimize=True)
    tailles = [image_tuile(c) for c in ICO]
    tailles[-1].save(
        ASSETS / "jobhunter.ico", sizes=[(c, c) for c in ICO], append_images=tailles[:-1]
    )
    print(
        f"{len(svgs())} SVG dans docs/brand, icônes de l'app refaites ({', '.join(map(str, ICO))} px)"
    )


if __name__ == "__main__":
    main()
