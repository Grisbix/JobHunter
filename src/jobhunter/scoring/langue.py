"""jobhunter.scoring.langue — Is the posting in English or in French?

Formerly Scripts/langue.py.

WHY. 2492 offers of the queue are abroad and most of them are written in English.
Sending them a CV and a letter in French disqualifies you before reading.

METHOD: FUNCTION WORDS, not professional vocabulary. "analyst", "finance", "ESG",
"reporting" and "data" are identical in both languages and saturate the sector's
French postings — counting those words would pass half of the Paris offers off as
English. The articles, prepositions and auxiliaries, on the other hand, do not lie: a
French sentence carries "le", "des", "pour", "vous"; an English sentence carries
"the", "of", "with", "you".

In case of a tie or a text that is too short: FRENCH. It is the language of most of
the queue, and erring towards French on a French offer costs less than sending an
English CV to an SME in the Gironde.

Run:
  python -m jobhunter.scoring.langue            # distribution of the queue
"""

import re
import sys

# Function words: frequent, short, and specific to each language.
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


# FRANCE IS KNOWN BY `zones.zone_lieu`. First attempt: a list
# of cities written here. It missed "Grenoble (38) · Auvergne-Rhone-Alpes" and
# "33700 Merignac · Nouvelle-Aquitaine", two French offers promised an
# English CV. `zones.py` already holds the communes of Île-de-France, the Bordeaux
# area, the south-east and the country detector — a THIRD list of the same
# places would have diverged from the two others, as two lists that must agree
# always diverge.
#
# Only what `zones` cannot know remains here: where one works in
# francais HORS de France.
_RX_FRANCOPHONE_ETRANGER = re.compile(
    r"\bluxembourg\b|\bmonaco\b|\bbruxelles\b|\bwallonie\b|\bnamur\b|\bli[eè]ge\b|"
    r"\bsuisse\b|\bswitzerland\b|\bgen[eè]ve\b|\bgeneva\b|\blausanne\b|"
    r"\bneuch[aâ]tel\b|\bfribourg\b|\bqu[ée]bec\b|\bmontr[ée]al\b",
    re.I,
)
# German- or Italian-speaking: Switzerland is no longer French-speaking there.
_RX_CH_NON_FR = re.compile(
    r"\bz[uü]rich\b|\bbasel\b|\bb[aâ]le\b|\bbern\b|\bberne\b|"
    r"\bzug\b|\bluzern\b|\bst\.?\s*gallen\b|\blugano\b",
    re.I,
)


def langue_offre(
    titre: str | None = "", description: str | None = "", lieu: str | None = ""
) -> str:
    """'en' or 'fr'. The doubt benefits French, UNLESS the place contradicts it.

    `lieu`: the offer's location. Measured on 2026-09-22 — after widening to twelve
    countries, 1,809 foreign offers out of 1,814 were classified "fr", hence promised
    a French CV. LinkedIn's public search only returns the title and the place; the
    text is always too short to decide, and the 120-character rule fell back on French.

    A French CV sent to Stockholm or Frankfurt disqualifies you before reading. When
    the text says nothing, it is therefore the PLACE that decides.
    """
    t = f"{titre or ''} {description or ''}"
    # Below 120 characters, a title alone decides nothing: "ESG Analyst"
    # is written the same on both sides of the Channel. We then ask the place.
    if len(t.strip()) < 120:
        L = str(lieu or "").strip()
        if not L:
            return "fr"  # nothing to decide: previous behaviour
        # Deferred import: `zones` imports `job_sources` for its country
        # detector, and this module is imported early by the generators.
        try:
            from jobhunter.scoring.zones import INCONNU, INTERNATIONAL, zone_lieu

            z = zone_lieu(L)
        except Exception:
            z = None
        if z is not None and z not in (INTERNATIONAL, INCONNU):
            return "fr"  # a French place, whatever the zone
        if _RX_CH_NON_FR.search(L):
            return "en"
        return "fr" if _RX_FRANCOPHONE_ETRANGER.search(L) else "en"
    fr = len(_RX_FR.findall(t))
    en = len(_RX_EN.findall(t))
    # 20% margin required: a French text often quotes English titles
    # ("Sustainable Finance Analyst", "reporting"), and the opposite is rare.
    return "en" if en > fr * 1.2 else "fr"


def main() -> int:
    """Ligne de commande : bilan des langues détectées dans la file."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper
    import collections

    from jobhunter.stockage import file as queue_io

    q = queue_io.charger()
    c: collections.Counter[str] = collections.Counter()
    par_zone: collections.defaultdict[str, collections.Counter[str]] = collections.defaultdict(
        collections.Counter
    )
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
