"""Signature of the published versions: Ed25519, in pure Python.

Why. The update downloads code from GitHub. HTTPS guarantees that it comes from
GitHub, not that it comes from the author: a compromised account or workflow would
publish a booby-trapped version that every installation would take. The signature is
made **outside GitHub**, with a private key that never leaves the author's computer
(`outils/signature.py`); the application only knows the public key, written here.

What is signed: the **manifest** of a version — its number, the SHA-256 fingerprint of
each file of the program (the ZIP of the `v<version>` tag) and that of
`JobHunterSetup.exe`. It is published with the release, in `signature.json`.

As long as `CLE_PUBLIQUE` is empty, no version is signed: the update happens as before
and says so. As soon as it is set, a version without a valid signature is refused.

The algorithm is that of RFC 8032 (section 6), without a dependency: checking a
signature takes a few milliseconds.

Decision: docs/adr/0012-signed-updates.md
"""

import hashlib
import json
from typing import Any

# The author's public key (64 hexadecimal characters), set by
# `python outils/signature.py cle`. Empty = unsigned versions.
CLE_PUBLIQUE = ""

FICHIER = "signature.json"  # name of the release asset


class SignatureInvalide(Exception):
    """The downloaded version is not the one the author signed."""


# ── Ed25519 (RFC 8032, section 6) ───────────────────────────────────────────

_P = 2**255 - 19
_Q = 2**252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_RACINE_M1 = pow(2, (_P - 1) // 4, _P)

_Point = tuple[int, int, int, int]


def _ajouter(a: _Point, b: _Point) -> _Point:
    x = (a[1] - a[0]) * (b[1] - b[0]) % _P
    y = (a[1] + a[0]) * (b[1] + b[0]) % _P
    c = 2 * a[3] * b[3] * _D % _P
    d = 2 * a[2] * b[2] % _P
    e, f, g, h = y - x, d - c, d + c, y + x
    return (e * f % _P, g * h % _P, f * g % _P, e * h % _P)


def _multiplier(s: int, p: _Point) -> _Point:
    q: _Point = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            q = _ajouter(q, p)
        p = _ajouter(p, p)
        s >>= 1
    return q


def _egaux(a: _Point, b: _Point) -> bool:
    return (a[0] * b[2] - b[0] * a[2]) % _P == 0 and (a[1] * b[2] - b[1] * a[2]) % _P == 0


def _x(y: int, signe: int) -> int | None:
    if y >= _P:
        return None
    x2 = (y * y - 1) * pow(_D * y * y + 1, _P - 2, _P)
    if x2 == 0:
        return None if signe else 0
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P != 0:
        x = x * _RACINE_M1 % _P
    if (x * x - x2) % _P != 0:
        return None
    if (x & 1) != signe:
        x = _P - x
    return x


_GY = 4 * pow(5, _P - 2, _P) % _P
_GX = _x(_GY, 0) or 0
_G: _Point = (_GX, _GY, 1, _GX * _GY % _P)


def _compresser(p: _Point) -> bytes:
    zinv = pow(p[2], _P - 2, _P)
    x, y = p[0] * zinv % _P, p[1] * zinv % _P
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _decompresser(s: bytes) -> _Point | None:
    if len(s) != 32:
        return None
    y = int.from_bytes(s, "little")
    signe = y >> 255
    y &= (1 << 255) - 1
    x = _x(y, signe)
    return None if x is None else (x, y, 1, x * y % _P)


def _h(donnees: bytes) -> int:
    return int.from_bytes(hashlib.sha512(donnees).digest(), "little") % _Q


def _etendre(secret: bytes) -> tuple[int, bytes]:
    if len(secret) != 32:
        raise ValueError("clé privée de 32 octets attendue")
    h = hashlib.sha512(secret).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def publique(secret: bytes) -> bytes:
    """The public key (32 bytes) of a private key (32 bytes)."""
    a, _ = _etendre(secret)
    return _compresser(_multiplier(a, _G))


def signer(secret: bytes, message: bytes) -> bytes:
    """Signature Ed25519 (64 octets) de `message`."""
    a, prefixe = _etendre(secret)
    cle = _compresser(_multiplier(a, _G))
    r = _h(prefixe + message)
    rs = _compresser(_multiplier(r, _G))
    s = (r + _h(rs + cle + message) * a) % _Q
    return rs + int.to_bytes(s, 32, "little")


def verifier(cle: bytes, message: bytes, signature: bytes) -> bool:
    """True if `signature` is that of `message` by the holder of `cle`."""
    if len(cle) != 32 or len(signature) != 64:
        return False
    a = _decompresser(cle)
    r = _decompresser(signature[:32])
    if a is None or r is None:
        return False
    s = int.from_bytes(signature[32:], "little")
    if s >= _Q:
        return False
    h = _h(signature[:32] + cle + message)
    return _egaux(_multiplier(s, _G), _ajouter(r, _multiplier(h, a)))


# ── Manifest of a version ────────────────────────────────────────────────────


def octets(manifeste: dict[str, Any]) -> bytes:
    """The signed canonical form: sorted JSON, without spaces."""
    return json.dumps(manifeste, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def manifeste(version: str, fichiers: dict[str, bytes], setup: bytes | None) -> dict[str, Any]:
    """What is signed for a version: its files and its installer, by fingerprint."""
    return {
        "version": version,
        "fichiers": {rel: hashlib.sha256(b).hexdigest() for rel, b in sorted(fichiers.items())},
        "setup": hashlib.sha256(setup).hexdigest() if setup is not None else None,
    }


def emballer(secret: bytes, m: dict[str, Any]) -> bytes:
    """The content of `signature.json`: the manifest and its signature."""
    sig = signer(secret, octets(m)).hex()
    return json.dumps({"manifeste": m, "signature": sig}, indent=1, sort_keys=True).encode()


def ouvrir(contenu: bytes, version: str, cle_hex: str | None = None) -> dict[str, Any]:
    """The manifest of `signature.json`, if its signature is valid for this version.

    Raises:
        SignatureInvalide: unreadable file, wrong signature, or manifest of another
            version (an old signature replayed to roll back).
    """
    cle_hex = CLE_PUBLIQUE if cle_hex is None else cle_hex
    try:
        doc = json.loads(contenu)
        m, sig = doc["manifeste"], bytes.fromhex(doc["signature"])
        cle = bytes.fromhex(cle_hex)
    except (ValueError, KeyError, TypeError) as e:
        raise SignatureInvalide(f"{FICHIER} illisible ({type(e).__name__})") from e
    if not isinstance(m, dict) or not verifier(cle, octets(m), sig):
        raise SignatureInvalide("signature fausse : cette version n'est pas celle de l'auteur")
    if m.get("version") != version:
        raise SignatureInvalide(f"signature de la version {m.get('version')}, pas de la {version}")
    return m


def controler_fichiers(m: dict[str, Any], fichiers: dict[str, bytes]) -> None:
    """Each downloaded file is in the manifest, with the same fingerprint, and nothing is missing.

    Raises:
        SignatureInvalide: the first discrepancy found.
    """
    attendus = m.get("fichiers") or {}
    for rel, b in fichiers.items():
        if attendus.get(rel) != hashlib.sha256(b).hexdigest():
            raise SignatureInvalide(f"{rel} diffère de la version signée")
    manquants = sorted(set(attendus) - set(fichiers))
    if manquants:
        raise SignatureInvalide(f"{manquants[0]} manque au téléchargement")


def controler_setup(m: dict[str, Any], setup: bytes) -> None:
    """The downloaded installer is the one the author signed.

    Raises:
        SignatureInvalide: fingerprint missing or different.
    """
    if not m.get("setup") or m["setup"] != hashlib.sha256(setup).hexdigest():
        raise SignatureInvalide("JobHunterSetup.exe diffère de la version signée")
