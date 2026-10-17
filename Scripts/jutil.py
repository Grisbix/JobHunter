#!/usr/bin/env python3
"""jutil.py — utilitaires partagés : écriture ATOMIQUE, verrou, chemins, texte.

Un crash/kill au milieu d'une écriture ne corrompt jamais apply_queue.json.

Ce module existe aussi pour héberger les helpers que chaque programme réécrivait
de son côté. Ce n'est pas de l'esthétique : les copies DIVERGENT, et cette
divergence a déjà produit des bugs réels — une comparaison sensible à la casse
d'un côté et insensible de l'autre, une normalisation d'accents présente ici et
absente là, deux décodages `file:///` dont l'un oubliait la forme `file://`.
"""

import re
import sys
import unicodedata
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


# ── Normalisation de texte ───────────────────────────────────────────────────
def sans_accent(s):
    """Minuscules sans accents, via NFD.

    Remplace des tables manuelles qui oubliaient la moitie des lettres
    (« ë », « ï », « ù », « ü » n'y figuraient pas).
    """
    s = unicodedata.normalize("NFD", str(s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def cle(s):
    """Clé de comparaison : minuscules, blancs normalises. GARDE les accents.

    Volontairement distincte de `sans_accent` : cette fonction sert de cle de
    DEDUPLICATION de la queue. Lui faire ignorer les accents fusionnerait des
    offres aujourd'hui distinctes — un changement de comportement, pas un
    nettoyage. Utiliser `sans_accent(cle(s))` quand on veut les deux.
    """
    return re.sub(r"\s+", " ", (s or "").strip().lower())


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


def verifier_motifs(espace, minimum=1):
    """Refuse de demarrer si une regex du module porte un `\\b` corrompu.

    Une frontiere de mot se corrompt de deux facons, toutes deux SILENCIEUSES —
    le motif compile, ne leve rien, et ne matche plus jamais :
      \\x08          un \\b passe dans un heredoc shell devient un backspace
      \\\\b (litteral) une « correction » du cas precedent qui echappe l'antislash

    `job_sources` avait ce controle, pas `ats_match` — et c'est `ats_match` qui
    l'avait attrape : son `_ESG_TITLE_RX` commencait par un backspace, donc le
    plafond de fit ne se levait JAMAIS pour un intitule ESG. Le scoring tournait
    depuis on ne sait quand avec sa regle principale morte. D'ou cette version
    partagee : un garde-fou recopie a la main dans chaque module finit par
    manquer la ou il sert.

    Appel type, en FIN de module (globals() doit etre complet) :

        jutil.verifier_motifs(globals(), minimum=6)

    `minimum` : nombre de motifs attendus. Si la selection cesse de rien trouver,
    le controle rassurerait sans rien verifier — on prefere qu'il crie.
    """
    import re as _re

    vus = 0
    for nom, val in list(espace.items()):
        if not isinstance(val, _re.Pattern) or not isinstance(val.pattern, str):
            continue
        vus += 1
        assert "\x08" not in val.pattern, f"{nom} : backspace au lieu de \\b"
        assert "\\\\b" not in val.pattern, f"{nom} : antislash litteral au lieu de \\b"
    assert vus >= minimum, f"verifier_motifs ne voit que {vus} motifs (>= {minimum} attendus)"
    return vus
