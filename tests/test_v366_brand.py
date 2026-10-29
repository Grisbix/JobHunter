"""3.66: one logo, a target with a check, drawn by tools/brand.py in every form."""

import struct
import xml.etree.ElementTree as ET
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
BRAND = RACINE / "docs" / "brand"
ASSETS = RACINE / "src" / "jobhunter" / "app" / "assets"
SVG = "{http://www.w3.org/2000/svg}"


def _png(chemin: Path) -> tuple[int, int]:
    data = chemin.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", data[16:24])


def test_chaque_forme_du_logo_est_un_svg_valide_sans_police():
    attendus = {
        f"jobhunter-{f}.svg"
        for f in (
            "tile",
            "mark-light",
            "mark-dark",
            "mark-mono",
            "stacked-light",
            "stacked-dark",
            "inline-light",
            "inline-dark",
        )
    }
    assert attendus <= {p.name for p in BRAND.glob("*.svg")}
    for nom in attendus:
        racine = ET.parse(BRAND / nom).getroot()
        assert racine.tag == f"{SVG}svg" and racine.get("viewBox")
        # The name is drawn as outlines: no text that depends on an installed font.
        assert not list(racine.iter(f"{SVG}text"))


def test_les_couleurs_sont_celles_du_logo():
    tuile = (BRAND / "jobhunter-tile.svg").read_text(encoding="utf-8")
    assert "#4f46e5" in tuile and "#fb7185" in tuile
    assert "currentColor" in (BRAND / "jobhunter-mark-mono.svg").read_text(encoding="utf-8")


def test_les_icones_de_l_app_viennent_du_meme_dessin():
    assert _png(ASSETS / "jobhunter.png") == (256, 256)
    assert _png(RACINE / "src" / "jobhunter" / "web" / "static" / "logo.png") == (256, 256)
    assert _png(BRAND / "store-300.png") == (300, 300)
    data = (ASSETS / "jobhunter.ico").read_bytes()
    n = struct.unpack("<H", data[4:6])[0]
    assert {data[6 + 16 * i] or 256 for i in range(n)} == {16, 24, 32, 48, 64, 128, 256}


def test_le_generateur_rend_les_svg_commites():
    """The committed SVGs are exactly what tools/brand.py writes (fontTools present only)."""
    import importlib.util

    import pytest

    pytest.importorskip("fontTools")
    if not Path("C:/Windows/Fonts/segoeuib.ttf").is_file():
        pytest.skip("Segoe UI Bold: Windows only")
    spec = importlib.util.spec_from_file_location("brand", RACINE / "tools" / "brand.py")
    assert spec and spec.loader
    brand = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(brand)
    for nom, contenu in brand.svgs().items():
        assert (BRAND / nom).read_text(encoding="utf-8") == contenu, nom
