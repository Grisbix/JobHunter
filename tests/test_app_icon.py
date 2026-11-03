"""JobHunter has its own icon (3.19.1), shipped in jobhunter/assets since 3.77."""

import struct

from jobhunter.web.__main__ import ICONE


def test_icone_livree_avec_le_paquet():
    assert ICONE.with_suffix(".png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    data = ICONE.read_bytes()
    reserve, genre, n = struct.unpack("<HHH", data[:6])
    assert (reserve, genre) == (0, 1)  # an icon file
    cotes = {data[6 + 16 * i] or 256 for i in range(n)}  # width byte, 0 means 256
    assert {16, 32, 48, 256} <= cotes


def test_une_seule_icone_pour_tous():
    from jobhunter import welcome
    from jobhunter.programs import shortcut

    assert welcome.ICONE == shortcut.ICONE == ICONE
