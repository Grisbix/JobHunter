"""Signature des versions publiées : Ed25519, en Python pur.

Pourquoi. La mise à jour télécharge du code depuis GitHub. HTTPS garantit qu'il vient de
GitHub, pas qu'il vient de l'auteur : un compte ou un workflow compromis publierait une
version piégée que toutes les installations prendraient. La signature est faite **hors
de GitHub**, avec une clé privée qui ne quitte pas l'ordinateur de l'auteur
(`outils/signature.py`) ; l'application ne connaît que la clé publique, écrite ici.

Ce qui est signé : le **manifeste** d'une version — son numéro, l'empreinte SHA-256 de
chaque fichier du programme (le ZIP de l'étiquette `v<version>`) et celle de
`JobHunterSetup.exe`. Il est publié avec la release, dans `signature.json`.

Tant que `CLE_PUBLIQUE` est vide, aucune version n'est signée : la mise à jour se fait
comme avant et le dit. Dès qu'elle est posée, une version sans signature valide est
refusée.

L'algorithme est celui de la RFC 8032 (section 6), sans dépendance : la vérification
d'une signature prend quelques millisecondes.

Décision : docs/adr/0012-mises-a-jour-signees.md
"""

import hashlib
import json
from typing import Any

# Clé publique de l'auteur (64 caractères hexadécimaux), posée par
# `python outils/signature.py cle`. Vide = versions non signées.
CLE_PUBLIQUE = ""

FICHIER = "signature.json"  # nom de l'asset de la release


class SignatureInvalide(Exception):
    """La version téléchargée n'est pas celle que l'auteur a signée."""


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
    """La clé publique (32 octets) d'une clé privée (32 octets)."""
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
    """True si `signature` est celle de `message` par le détenteur de `cle`."""
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


# ── Manifeste d'une version ─────────────────────────────────────────────────


def octets(manifeste: dict[str, Any]) -> bytes:
    """La forme canonique signée : JSON trié, sans espaces."""
    return json.dumps(manifeste, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def manifeste(version: str, fichiers: dict[str, bytes], setup: bytes | None) -> dict[str, Any]:
    """Ce qu'on signe pour une version : ses fichiers et son installateur, par empreinte."""
    return {
        "version": version,
        "fichiers": {rel: hashlib.sha256(b).hexdigest() for rel, b in sorted(fichiers.items())},
        "setup": hashlib.sha256(setup).hexdigest() if setup is not None else None,
    }


def emballer(secret: bytes, m: dict[str, Any]) -> bytes:
    """Le contenu de `signature.json` : le manifeste et sa signature."""
    sig = signer(secret, octets(m)).hex()
    return json.dumps({"manifeste": m, "signature": sig}, indent=1, sort_keys=True).encode()


def ouvrir(contenu: bytes, version: str, cle_hex: str | None = None) -> dict[str, Any]:
    """Le manifeste de `signature.json`, si sa signature est valide pour cette version.

    Raises:
        SignatureInvalide: fichier illisible, signature fausse, ou manifeste d'une autre
            version (une vieille signature rejouée pour faire revenir en arrière).
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
    """Chaque fichier téléchargé est dans le manifeste, à la même empreinte, et rien ne manque.

    Raises:
        SignatureInvalide: le premier écart trouvé.
    """
    attendus = m.get("fichiers") or {}
    for rel, b in fichiers.items():
        if attendus.get(rel) != hashlib.sha256(b).hexdigest():
            raise SignatureInvalide(f"{rel} diffère de la version signée")
    manquants = sorted(set(attendus) - set(fichiers))
    if manquants:
        raise SignatureInvalide(f"{manquants[0]} manque au téléchargement")


def controler_setup(m: dict[str, Any], setup: bytes) -> None:
    """L'installateur téléchargé est celui que l'auteur a signé.

    Raises:
        SignatureInvalide: empreinte absente ou différente.
    """
    if not m.get("setup") or m["setup"] != hashlib.sha256(setup).hexdigest():
        raise SignatureInvalide("JobHunterSetup.exe diffère de la version signée")
