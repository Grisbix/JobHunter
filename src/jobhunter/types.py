"""Types partages du moteur (phase 5 du plan).

Les offres et les candidatures restent des dict JSON : leur format sur disque ne change
pas. `Offre` et `Candidature` sont des `TypedDict` **non totaux** : toutes les cles sont
facultatives, parce qu'une offre se construit par etapes (la collecte pose entreprise,
poste et url ; le scoring, fit et zone ; la generation, cv et lettre) et que de vieilles
offres n'ont jamais recu les champs ajoutes depuis. Le typage nomme et type les champs ;
il ne rend rien obligatoire.

Inventaire du 2026-10-19 sur une vraie file (12 137 offres, 48 candidatures) et sur les
cles que le code lit ou ecrit. Une cle nouvelle s'ajoute ici avant d'etre ecrite.
"""

from os import PathLike
from typing import TypedDict


class Offre(TypedDict, total=False):
    """Une offre de la file (apply_queue.json)."""

    # identite et lien
    n: int
    entreprise: str
    poste: str
    url: str
    url_type: str  # "OFFRE", "RECHERCHE"…
    site_kind: str
    site_final: str  # lien du site employeur trouve par site_final
    url_linkedin: str
    url_home: str
    url_orig: str
    canal: str
    source: str
    # contenu de l'annonce
    description: str
    desc_partielle: bool  # extrait d'agregateur : une meilleure source le remplace
    missions: str
    profil: str
    process: str
    contrat: str
    localisation: str
    localisation_orig: str
    teletravail: str
    salaire: str
    date_publication: str
    peu_de_candidats: bool
    exp_requise: int
    is_stage: bool
    # decisions du moteur
    domaine: str
    fit: int
    fit_fin: float
    skills_match: int
    ats_pct: int | None
    zone: str
    pourquoi: str
    priorite: str
    action: str
    statut: str
    etat: str
    # disponibilite
    link_status: str
    ls_check: str  # date du dernier controle
    vu_le: str  # derniere fois qu'une source l'a resservie
    # documents et contact
    cv: str | None
    lettre: str | None
    cv_variant: str | None
    rh: str | None
    rh_orig: str
    rh_email: str


class Candidature(TypedDict, total=False):
    """Une entree de suivi.json."""

    s: str  # statut : « postulé », « entretien », « refus »…
    d: str  # date, AAAA-MM-JJ
    n: str  # note libre
    retiree: str  # date a laquelle l'offre a quitte la file


Suivi = dict[str, Candidature]
"""suivi.json entier, indexe par l'identite de l'offre (`queue_io.oid`)."""

Chemin = str | PathLike[str]
"""Tout ce qui designe un fichier : str ou Path."""
