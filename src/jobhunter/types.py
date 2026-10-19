"""Shared types of the engine (phase 5 of the plan).

Offers and applications remain JSON dicts: their on-disk format does not change.
`Offre` and `Candidature` are **non-total** `TypedDict`s: all keys are
optional, because an offer is built in stages (the collection sets company,
job and url; the scoring, fit and zone; the generation, cv and letter) and old
offers never received the fields added since. The typing names and types the fields;
it makes nothing mandatory.

Inventory of 2026-10-19 on a real queue (12,137 offers, 48 applications) and on the
keys the code reads or writes. A new key is added here before being written.
"""

from os import PathLike
from typing import TypedDict


class Offre(TypedDict, total=False):
    """An offer of the queue (apply_queue.json)."""

    # identity and link
    n: int
    entreprise: str
    poste: str
    url: str
    url_type: str  # "OFFRE", "RECHERCHE"…
    site_kind: str
    site_final: str  # link of the employer's site found by site_final
    url_linkedin: str
    url_home: str
    url_orig: str
    canal: str
    source: str
    # contenu de l'annonce
    description: str
    desc_partielle: bool  # aggregator excerpt: a better source replaces it
    missions: str
    profil: str
    process: str
    contrat: str
    localisation: str
    localisation_orig: str
    autres_lieux: list[str]  # same job published elsewhere (scan dedup)
    teletravail: str
    salaire: str
    date_publication: str
    peu_de_candidats: bool
    exp_requise: int
    is_stage: bool
    # engine decisions
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
    ls_check: str  # date of the last check
    vu_le: str  # last time a source served it again
    # documents and contact
    cv: str | None
    lettre: str | None
    cv_variant: str | None
    rh: str | None
    rh_orig: str
    rh_email: str


class Preuve(TypedDict, total=False):
    """What the page displayed after the sending declaration (ADR 0009)."""

    texte: str  # the excerpt that justifies the state, or the reason for the uncertainty
    url: str
    capture: str  # path of the page screenshot, "" if impossible
    le: str  # date and time of the observation, ISO


class Candidature(TypedDict, total=False):
    """An entry of suivi.json."""

    s: str  # status: "postulé", "entretien", "refus"…
    d: str  # date, AAAA-MM-JJ
    n: str  # note libre
    retiree: str  # date on which the offer left the queue
    envoi: str  # "confirmé", "incertain" or "déclaré" (ADR 0009)
    preuve: Preuve
    courriel: "CourrielStatut"  # the email that justified the last status (2.20)


class CourrielStatut(TypedDict, total=False):
    """Le courriel qu'un statut proposé, puis accepté, cite (jobhunter.courriels)."""

    de: str  # sender
    sujet: str
    le: str  # date of the email, YYYY-MM-DD


Suivi = dict[str, Candidature]
"""suivi.json entier, indexe par l'identite de l'offre (`queue_io.oid`)."""

Chemin = str | PathLike[str]
"""Tout ce qui designe un fichier : str ou Path."""
