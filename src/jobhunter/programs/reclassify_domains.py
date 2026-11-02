"""Gives each offer of the queue the domain its title calls, after the trades changed.

A trade added in the Profil screen (web.trades) is a new domain: the offers already in
the queue keep the domain they got at collection until this runs, and the Offres
screen's domain filter shows only the domains the offers carry.

Run:
  python -m jobhunter.programs.reclassify_domains
"""

import sys


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    from jobhunter.programs.first_launch import reclasser_domaines

    n = reclasser_domaines()
    print(f"{n} offre(s) changent de domaine.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
