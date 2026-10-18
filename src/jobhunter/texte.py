"""Normalisation de texte et garde-fou des motifs (ex-helpers de Scripts/jutil.py).

Les copies de ces fonctions DIVERGEAIENT d'un programme a l'autre : une comparaison
sensible a la casse ici, insensible la, une table d'accents qui oubliait la moitie
des lettres. Une seule version, partout.
"""

import re
import unicodedata


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
