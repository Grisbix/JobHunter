#!/usr/bin/env python3
"""jutil.py — utilitaires partagés : écriture ATOMIQUE, verrou, chemins, texte.

Un crash/kill au milieu d'une écriture ne corrompt jamais apply_queue.json.

Ce module existe aussi pour héberger les helpers que chaque programme réécrivait
de son côté. Ce n'est pas de l'esthétique : les copies DIVERGENT, et cette
divergence a déjà produit des bugs réels — une comparaison sensible à la casse
d'un côté et insensible de l'autre, une normalisation d'accents présente ici et
absente là, deux décodages `file:///` dont l'un oubliait la forme `file://`.
"""

import sys
from pathlib import Path
from urllib.parse import quote, unquote

# Le moteur migre vers src/jobhunter (phase 3) ; tant que les programmes sont lances
# depuis Scripts/, ce dossier doit etre importable.
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Le verrou vit dans jobhunter.stockage.verrou ; ces noms restent ceux de toujours.
from jobhunter.stockage import atomique as _atomique  # noqa: E402
from jobhunter.stockage.verrou import (  # noqa: E402, F401
    _TENUS,
    _fverrou,
    _pid_vivant,
    garder,
    prendre_verrou,
    rendre_verrou,
    tenu,
)
from jobhunter.texte import cle, sans_accent, verifier_motifs  # noqa: E402, F401


# ── Chemins ↔ URL file:/// ───────────────────────────────────────────────────
def chemin_de(u):
    """URL `file:///…` (ou chemin nu) → Path. None si vide.

    Gere `file:///` ET `file://` : trois des six copies precedentes ne
    traitaient que la premiere forme et rendaient un chemin commencant par
    « / », donc introuvable.
    """
    if not u:
        return None
    s = str(u)
    for prefixe in ("file:///", "file://"):
        if s.startswith(prefixe):
            s = s[len(prefixe) :]
            break
    return Path(unquote(s))


def url_de(p):
    """Path → URL `file:///…`, séparateurs Windows convertis."""
    return "file:///" + quote(str(p).replace("\\", "/"), safe="/:")


def existe(u):
    """Le document désigné par cette URL/ce chemin est-il sur le disque ?"""
    p = chemin_de(u)
    try:
        return bool(p and p.exists())
    except OSError:  # chemin invalide pour l'OS (trop long, caracteres interdits)
        return False


def jwrite(path, obj, _brut=False):
    """Ecriture atomique : on ecrit a cote, puis on bascule d'un seul coup.

    DEUX GARDES, chacune pour une panne observee.

    1. La QUEUE ne doit jamais reprendre les descriptions en ligne. Elles vivent
       dans descriptions.json depuis la separation ; queue_io.charger() les
       reinjecte en memoire pour le travail, et queue_io.sauver() les ressort
       avant d'ecrire. Onze programmes appellent jwrite(QUEUE, ...) en direct :
       chacun d'eux remettait les textes dans le fichier, et la queue etait
       repassee de 2,9 Mo a 15,9 Mo sans que rien ne signale la regression.
       Plutot que de compter sur onze appelants pour y penser, on redirige ici.

    2. os.replace echoue en PermissionError sous Windows quand OneDrive, un
       antivirus ou l'app tient encore un handle sur le fichier. L'echec est
       transitoire : on reessaie quelques fois avant d'abandonner.
    """
    path = Path(path)
    # _brut : queue_io a DEJA fait la separation et nous redonne la main pour
    # l'ecriture. Sans ce drapeau, sa propre ecriture repassait par la garde et
    # se rappelait a l'infini (RecursionError) des que le chemin n'etait pas le
    # fichier canonique — un fichier de test, par exemple.
    if (
        not _brut
        and path.name == "apply_queue.json"
        and isinstance(obj, list)
        and any(isinstance(x, dict) and (x.get("description") or "").strip() for x in obj)
    ):
        from jobhunter.stockage import file

        return file.sauver(obj, path)
    _atomique.ecrire_json(path, obj)
