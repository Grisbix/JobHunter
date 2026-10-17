#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""langue.py — L'annonce est-elle en anglais ou en francais ?

POURQUOI. 2492 offres de la file sont a l'etranger et la plupart sont redigees
en anglais. Leur envoyer un CV et une lettre en francais, c'est se disqualifier
avant lecture.

METHODE : des MOTS-OUTILS, pas du vocabulaire metier. « analyst », « finance »,
« ESG », « reporting » et « data » sont identiques dans les deux langues et
saturent les annonces francaises du secteur — compter ces mots-la ferait passer
la moitie des offres parisiennes pour anglaises. Les articles, prepositions et
auxiliaires, eux, ne mentent pas : une phrase francaise porte « le », « des »,
« pour », « vous » ; une phrase anglaise porte « the », « of », « with », « you ».

En cas d'egalite ou de texte trop court : FRANCAIS. C'est la langue de la
majorite de la file, et se tromper vers le francais sur une offre francaise
coute moins qu'envoyer un CV anglais a une PME de Gironde.

Run :
  python langue.py            # repartition de la file
"""

import sys
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# Mots-outils : frequents, courts, et propres a chaque langue.
_FR = (
    r"\b(le|la|les|des|du|une|un|et|ou|dans|pour|avec|sur|par|au|aux|ce|cette"
    r"|vous|nous|votre|notre|est|sont|sera|plus|tous|toute|afin|ainsi|chez"
    r"|entre|sous|leur|leurs|qui|que|dont|vos|nos)\b"
)
_EN = (
    r"\b(the|of|and|to|in|for|with|on|at|as|is|are|will|be|you|your|we|our"
    r"|this|that|from|by|an|a|have|has|their|they|its|it|or|about|across"
    r"|within|including|role|team)\b"
)

_RX_FR = re.compile(_FR, re.I)
_RX_EN = re.compile(_EN, re.I)


# LA FRANCE, C'EST `zones.zone_lieu` QUI LA CONNAIT. Premier essai : une liste
# de villes ecrite ici. Elle ratait « Grenoble (38) · Auvergne-Rhone-Alpes » et
# « 33700 Merignac · Nouvelle-Aquitaine », deux offres francaises promises a un
# CV anglais. `zones.py` tient deja les communes d'Ile-de-France, le bassin
# bordelais, le sud-est et le detecteur de pays — une TROISIEME liste des memes
# lieux aurait diverge des deux autres, comme divergent toujours deux listes
# qui doivent s'accorder.
#
# Ne reste ici que ce que `zones` ne peut pas savoir : ou l'on travaille en
# francais HORS de France.
_RX_FRANCOPHONE_ETRANGER = re.compile(
    r"\bluxembourg\b|\bmonaco\b|\bbruxelles\b|\bwallonie\b|\bnamur\b|\bli[eè]ge\b|"
    r"\bsuisse\b|\bswitzerland\b|\bgen[eè]ve\b|\bgeneva\b|\blausanne\b|"
    r"\bneuch[aâ]tel\b|\bfribourg\b|\bqu[ée]bec\b|\bmontr[ée]al\b",
    re.I,
)
# Alemanique ou italophone : la Suisse n'y est plus francophone.
_RX_CH_NON_FR = re.compile(
    r"\bz[uü]rich\b|\bbasel\b|\bb[aâ]le\b|\bbern\b|\bberne\b|"
    r"\bzug\b|\bluzern\b|\bst\.?\s*gallen\b|\blugano\b",
    re.I,
)


def langue_offre(titre="", description="", lieu=""):
    """'en' ou 'fr'. Le doute profite au francais, SAUF si le lieu le dement.

    `lieu` : la localisation de l'offre. Mesure du 2026-09-22 — apres
    l'elargissement a douze pays, 1 809 offres etrangeres sur 1 814 etaient
    classees « fr », donc promises a un CV francais. La recherche publique
    LinkedIn ne rend que le titre et le lieu ; le texte est toujours trop court
    pour trancher, et la regle des 120 caracteres retombait sur le francais.

    Un CV francais envoye a Stockholm ou a Francfort, c'est se disqualifier
    avant lecture. Quand le texte ne dit rien, c'est donc le LIEU qui tranche.
    """
    t = f"{titre or ''} {description or ''}"
    # Sous 120 caracteres, un intitule seul ne tranche rien : « ESG Analyst »
    # est ecrit pareil des deux cotes de la Manche. On interroge alors le lieu.
    if len(t.strip()) < 120:
        L = str(lieu or "").strip()
        if not L:
            return "fr"  # rien pour decider : comportement d'avant
        # Import differe : `zones` importe `job_sources` pour son detecteur de
        # pays, et ce module-ci est importe tot par les generateurs.
        try:
            from zones import zone_lieu, INTERNATIONAL, INCONNU

            z = zone_lieu(L)
        except Exception:
            z = None
        if z is not None and z not in (INTERNATIONAL, INCONNU):
            return "fr"  # un lieu francais, quelle que soit la zone
        if _RX_CH_NON_FR.search(L):
            return "en"
        return "fr" if _RX_FRANCOPHONE_ETRANGER.search(L) else "en"
    fr = len(_RX_FR.findall(t))
    en = len(_RX_EN.findall(t))
    # Marge de 20 % exigee : un texte francais cite souvent des titres anglais
    # (« Sustainable Finance Analyst », « reporting »), et l'inverse est rare.
    return "en" if en > fr * 1.2 else "fr"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    import queue_io
    import collections

    q = queue_io.charger()
    c = collections.Counter()
    par_zone = collections.defaultdict(collections.Counter)
    for o in q:
        lg = langue_offre(o.get("poste"), o.get("description"))
        c[lg] += 1
        par_zone[o.get("zone") or "?"][lg] += 1
    print(f"{len(q)} offres · {c['fr']} en francais · {c['en']} en anglais\n")
    for z, cc in sorted(par_zone.items()):
        print(f"  {z:14} fr {cc['fr']:5}   en {cc['en']:5}")
    print("\nExemples classes ANGLAIS :")
    n = 0
    for o in q:
        if langue_offre(o.get("poste"), o.get("description")) == "en" and n < 8:
            print(
                f"  {(o.get('entreprise') or '')[:22]:22} {(o.get('poste') or '')[:44]:44} "
                f"{(o.get('localisation') or '')[:22]}"
            )
            n += 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
