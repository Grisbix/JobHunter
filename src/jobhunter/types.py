"""Types partages du moteur (phase 5 du plan).

Les offres et les candidatures restent des dict JSON : leur format sur disque ne change
pas. Ces alias nomment ce qui circule ; ils deviendront des `TypedDict` champ par champ,
quand chaque cle aura ete inventoriee (une offre en porte une trentaine, toutes
facultatives).
"""

from os import PathLike
from typing import Any

Offre = dict[str, Any]
"""Une offre de la file (apply_queue.json) : entreprise, poste, url, fit, zone..."""

Candidature = dict[str, Any]
"""Une entree de suivi.json : statut `s`, date `d`, note, relances..."""

Suivi = dict[str, Candidature]
"""suivi.json entier, indexe par l'identite de l'offre (`queue_io.oid`)."""

Chemin = str | PathLike[str]
"""Tout ce qui designe un fichier : str ou Path."""
