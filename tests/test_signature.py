"""Signature des versions (jobhunter.signature) : Ed25519 conforme, manifeste contrôlé."""

import hashlib
import json

import pytest

from jobhunter import signature as sig

# RFC 8032, section 7.1, tests 1 and 2.
VECTEURS = [
    (
        "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
        "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
        "",
        "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155"
        "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b",
    ),
    (
        "4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb",
        "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c",
        "72",
        "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da"
        "085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00",
    ),
]


@pytest.mark.parametrize(("secret", "public", "message", "signe"), VECTEURS)
def test_vecteurs_rfc8032(secret, public, message, signe):
    s, m = bytes.fromhex(secret), bytes.fromhex(message)
    assert sig.publique(s).hex() == public
    assert sig.signer(s, m).hex() == signe
    assert sig.verifier(bytes.fromhex(public), m, bytes.fromhex(signe))


def test_signature_alteree_refusee():
    s = bytes(range(32))
    cle, m = sig.publique(s), b"JobHunter 2.18.0"
    bonne = sig.signer(s, m)
    assert sig.verifier(cle, m, bonne)
    assert not sig.verifier(cle, m + b"!", bonne)
    assert not sig.verifier(cle, m, bonne[:-1] + bytes([bonne[-1] ^ 1]))
    assert not sig.verifier(sig.publique(bytes(32)), m, bonne)
    assert not sig.verifier(cle, m, bonne[:63])


SECRET = bytes(range(1, 33))
CLE = sig.publique(SECRET).hex()
FICHIERS = {"VERSION": b"2.18.0\n", "src/jobhunter/a.py": b"A = 1\n"}
SETUP = b"MZ installateur"


def signe(version="2.18.0", fichiers=FICHIERS, setup=SETUP):
    return sig.emballer(SECRET, sig.manifeste(version, fichiers, setup))


def test_manifeste_valide():
    m = sig.ouvrir(signe(), "2.18.0", CLE)
    sig.controler_fichiers(m, FICHIERS)
    sig.controler_setup(m, SETUP)
    assert m["fichiers"]["VERSION"] == hashlib.sha256(b"2.18.0\n").hexdigest()


def test_fichier_modifie_refuse():
    m = sig.ouvrir(signe(), "2.18.0", CLE)
    with pytest.raises(sig.SignatureInvalide, match="a.py"):
        sig.controler_fichiers(m, {**FICHIERS, "src/jobhunter/a.py": b"A = 2\n"})


def test_fichier_ajoute_ou_manquant_refuse():
    m = sig.ouvrir(signe(), "2.18.0", CLE)
    with pytest.raises(sig.SignatureInvalide, match="piege"):
        sig.controler_fichiers(m, {**FICHIERS, "src/jobhunter/piege.py": b"x"})
    with pytest.raises(sig.SignatureInvalide, match="manque"):
        sig.controler_fichiers(m, {"VERSION": FICHIERS["VERSION"]})


def test_installateur_modifie_refuse():
    m = sig.ouvrir(signe(), "2.18.0", CLE)
    with pytest.raises(sig.SignatureInvalide):
        sig.controler_setup(m, SETUP + b"!")
    with pytest.raises(sig.SignatureInvalide):
        sig.controler_setup(sig.ouvrir(signe(setup=None), "2.18.0", CLE), SETUP)


def test_manifeste_retouche_refuse():
    doc = json.loads(signe())
    doc["manifeste"]["fichiers"]["src/jobhunter/a.py"] = hashlib.sha256(b"A = 2\n").hexdigest()
    with pytest.raises(sig.SignatureInvalide, match="fausse"):
        sig.ouvrir(json.dumps(doc).encode(), "2.18.0", CLE)


def test_vieille_signature_rejouee_refusee():
    """A valid signature of 2.17 does not hold for 2.18 (rollback)."""
    with pytest.raises(sig.SignatureInvalide, match="2.17.0"):
        sig.ouvrir(signe("2.17.0"), "2.18.0", CLE)


def test_autre_cle_refusee():
    autre = sig.publique(bytes(32)).hex()
    with pytest.raises(sig.SignatureInvalide, match="fausse"):
        sig.ouvrir(signe(), "2.18.0", autre)


@pytest.mark.parametrize("contenu", [b"", b"{", b"[]", b'{"manifeste": {}, "signature": "zz"}'])
def test_fichier_illisible(contenu):
    with pytest.raises(sig.SignatureInvalide):
        sig.ouvrir(contenu, "2.18.0", CLE)
