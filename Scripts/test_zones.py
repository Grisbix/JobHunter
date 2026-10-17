#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_zones.py — zones.zone_lieu sur des lieux REELS de la file.

Chaque cas vient d'une offre mal rangee, mesuree le 2026-09-23 : 409 offres
etaient dans « le reste de la France » a tort (300 a l'etranger, 53 en IDF,
56 dans le Sud-Est). Sans reseau.

Run : python test_zones.py
"""

import _profil_test  # noqa: F401  — les tests tournent sur le profil d'exemple
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from zones import (
    zone_lieu,
    PRIORITAIRE as P,
    SECONDAIRE as S,
    AILLEURS as A,
    INTERNATIONAL as I,
    INCONNU as U,
)

CAS = [
    # pays ecrits en anglais par LinkedIn
    ("Bogota, D.C., Capital District, Colombia", I),
    ("Santiago, Santiago Metropolitan Region, Chile", I),
    ("Bangkok, Bangkok City, Thailand", I),
    ("Sofia, Sofia City, Bulgaria", I),
    ("Tekirdağ, Türkiye", I),
    ("Colombia", I),
    # metropoles sans pays
    ("Lisbon Metropolitan Area", I),
    ("Greater Milan Metropolitan Area", I),
    ("Greater Gothenburg Metropolitan Area", I),
    ("Cincinnati Metropolitan Area", I),
    ("Madrid, Remote", I),
    # ... mais les metropoles francaises restent francaises
    ("Greater Paris Metropolitan Region", P),
    ("Greater Lyon Area", S),
    ("Greater Lille Metropolitan Area", A),
    ("Greater Saint-Nazaire Area", A),
    # WTJ : « · France » est celui du site, le code pays dit la verite
    ("Genève · France", I),
    ("Zaventem, VLG, BE · France", I),
    ("Saint-Ouen, A8, FR · France", P),
    ("Biot, B8, FR · France", S),
    ("Vaulx-en-Velin, ARA, FR · France", S),
    ("Niort, NA, FR · France", A),
    # departements et codes postaux
    ("Bobigny - 93", P),
    ("Melun - 77", P),
    ("Télétravail à 94710 Maisons-Alfort", P),
    ("Pessac - 33", P),
    ("Bron - 69", S),
    ("Cluses (74) · France", S),
    ("Télétravail partiel à 82710 Bressols", S),
    ("Nantes - 44", A),
    ("Le Lamentin - 972", A),
    ("97600 Mamoudzou · France", A),
    # un code postal etranger ne devient pas un departement
    ("Houston, TX 77002", I),
    ("San Diego, CA 92101", I),
    # communes seules
    ("Maisons-Alfort", P),
    ("Palaiseau", P),
    ("Martillac", P),
    ("Valbonne", S),
    ("Lattes", S),
    ("Mauguio Languedoc-Roussillon FR", S),
    ("Colomiers Midi-Pyrenees FR", S),
    ("Lezennes, Hauts-de-France, France", A),  # banlieue de Lille, pas d'IDF
    # vague = inconnu, jamais un rejet
    ("France", U),
    ("", U),
    ("Remote (FR)", U),
    ("All France (remote)", U),
    ("Europe", U),
    # non-regressions
    ("Paris, Île-de-France, France", P),
    ("Courbevoie", P),
    ("Singapore, Singapore", I),  # « sinGAPore » n'est pas Gap
    ("Lille, Hauts-de-France, France", A),  # « de » n'est pas l'Allemagne
    ("POINTE NOIRE (CONGO)", I),
    ("Chasseneuil-du-Poitou, Nouvelle-Aquitaine, France", A),
    ("Rotterdam, South Holland, Netherlands", I),
    ("Machine Learning Hub, Toulouse", S),  # « Chine » dans « Machine »
    # homonymes d'IDF hors d'IDF
    ("Boulogne-sur-Mer", A),
    ("Boulogne Nord-Pas-de-Calais FR", A),
    ("Boulogne-Billancourt", P),
    ("Asnières, Normandy, France", A),
    ("Asnières-sur-Seine", P),
    ("Saint-Denis, Reunion", A),
    ("Saint-Denis", P),
]

# Etiquette de l'app : Bordeaux et IDF partagent la zone, pas le libelle.
from zones import sous_zone

for lieu, attendu in [
    ("Bordeaux, Nouvelle-Aquitaine, France", "bordeaux"),
    ("33700 Mérignac", "bordeaux"),
    ("Blanquefort - 33", "bordeaux"),
    ("Paris, Île-de-France, France", "idf"),
    ("Courbevoie", "idf"),
    ("Lyon", ""),
]:
    CAS.append((f"sous_zone:{lieu}", attendu))

# Filtre Pays de l'app : un nom francais par pays, quelle que soit la langue.
from zones import pays_lieu, ville_affichee

for lieu, attendu in [
    ("Geneva, Geneva, Switzerland", "Suisse"),
    ("Zürich", "Suisse"),
    ("GLASGOW (ROYAUME-UNI)", "Royaume-Uni"),
    ("POINTE NOIRE (CONGO)", "Congo"),
    ("Zaventem, VLG, BE · France", "Belgique"),
    ("Houston, TX 77002", "États-Unis"),
    ("New York City Metropolitan Area", "États-Unis"),
    ("Mexico City, Mexico", "Mexique"),
    ("Bogota, Colombia", "Colombie"),
    ("Lisbon Metropolitan Area", "Portugal"),
    ("Paris, Île-de-France, France", "France"),
    ("Nantes - 44", "France"),
    ("Remote", "?"),
    # Recontrole de la file le 2026-10-07
    ("France", "France"),
    ("All France (remote)", "France"),
    ("Birmingham, AL", "États-Unis"),
    ("New Orleans, LA", "États-Unis"),
    ("Dublin, OH", "États-Unis"),
    ("Rive-de-Gier", "France"),
    ("La Cañada, Querétaro, Mexico", "Mexique"),
    ("Mexicali, Baja California, Mexico", "Mexique"),
    ("Cerro Colorado, Arequipa, Peru", "Pérou"),
    ("Green Bay, Wisconsin Metropolitan Area", "États-Unis"),
    ("Albuquerque-Santa Fe Metropolitan Area", "États-Unis"),
    ("Delft Zuid-Holland NL", "Pays-Bas"),
    ("Arlington VA US", "États-Unis"),
    ("Port Louis, Mauritius", "Maurice"),
    ("Saint-Maurice-d’Ibie, Auvergne-Rhône-Alpes, France", "France"),
    ("Tbilisi, Georgia", "Géorgie"),
    ("Belfast", "Royaume-Uni"),
    ("Lahore, Punjab, Pakistan", "Pakistan"),
    ("Cracow Metropolitan Area", "Pologne"),
]:
    CAS.append((f"pays:{lieu}", attendu))
# Lieu affiche : toute l'IDF devient « Paris », le reste ne bouge pas.
for lieu, attendu in [
    ("La Défense - 92", "Paris"),
    ("Courbevoie", "Paris"),
    ("Greater Paris Metropolitan Region", "Paris"),
    ("Bordeaux, Nouvelle-Aquitaine, France", "Bordeaux, Nouvelle-Aquitaine, France"),
    ("Lyon", "Lyon"),
]:
    CAS.append((f"ville:{lieu}", attendu))

# Lieu effectif : l'intitule qui nomme une ville etrangere l'emporte sur un lieu
# francais (Numberly « VIE - New York » donnee a « Paris » par Talent).
from zones import lieu_effectif

for titre, lieu, attendu in [
    ("Forward Deployed Engineer (VIE - New York)", "Paris", "New York, États-Unis"),
    ("Forward Deployed Engineer (VIE - New York)", "Boston, MA", "Boston, MA"),
    ("Analyste ESG - couverture UK", "Paris", "Paris"),
    ("Analyste Marchés US", "Paris", "Paris"),
    ("Chargé RSE Porto-Vecchio", "Corse", "Corse"),
]:
    CAS.append((f"effectif:{titre}|{lieu}", attendu))

# Region du filtre de l'app (2026-10-07).
from zones import region_pays

for pays, attendu in [
    ("France", "Europe"),
    ("Royaume-Uni", "Europe"),
    ("États-Unis", "Amérique du Nord"),
    ("Mexique", "Amérique latine"),
    ("Singapour", "Asie"),
    ("Émirats arabes unis", "Moyen-Orient"),
    ("Gabon", "Afrique"),
    ("Australie", "Océanie"),
    ("?", "?"),
    ("étranger (autre)", "?"),
]:
    CAS.append((f"region:{pays}", attendu))

ok = ko = 0
for lieu, attendu in CAS:
    if lieu.startswith("effectif:"):
        ti, li = lieu[9:].split("|")
        r = lieu_effectif(li, ti)
    elif lieu.startswith("region:"):
        r = region_pays(lieu[7:])
    elif lieu.startswith("pays:"):
        r = pays_lieu(lieu[5:])
    elif lieu.startswith("ville:"):
        r = ville_affichee(lieu[6:])
    else:
        r = sous_zone(lieu[10:]) if lieu.startswith("sous_zone:") else zone_lieu(lieu)
    if r == attendu:
        ok += 1
    else:
        ko += 1
        print(f"❌ {lieu!r} → {r}, attendu {attendu}")
print(f"✅ {ok}/{ok + ko}")
sys.exit(1 if ko else 0)
