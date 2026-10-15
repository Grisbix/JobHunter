#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""queue_io.py — accès unique à apply_queue.json.

POURQUOI CE MODULE. Quatorze programmes écrivent la file, et chacun réimplémentait
la même séquence : prendre le verrou, relire le disque, modifier, écrire en
atomique, relâcher. Un seul l'oubliait — l'app — et c'était une perte de données
en puissance. Une séquence recopiée quatorze fois finit toujours par diverger.

    from queue_io import transaction, charger

    offres = charger()                     # lecture seule, pas de verrou

    with transaction() as offres:          # verrou + relecture fraîche
        for o in offres:
            o["fit"] = 10
    # sortie du bloc : écriture atomique, puis verrou relâché

NOM DU FICHIER. Surtout pas `queue.py` : `queue` est un module de la bibliothèque
standard, `Scripts/` est dans sys.path, et JobHunter.pyw fait `import queue`.
Le masquer casserait l'application.
"""
import json
import sys
from contextlib import contextmanager
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import jutil

CHEMIN = HERE / "apply_queue.json"

# ── Descriptions à part ──────────────────────────────────────────────────────
# Les descriptions pesaient 8,3 Mo des 11,6 Mo de la file, soit 64 %. Or les 13
# programmes qui modifient UNE offre réécrivaient le fichier ENTIER : 142 ms par
# cycle, dont l'essentiel à recopier des textes que personne n'avait touchés.
# Elles vivent donc dans un fichier annexe, indexé par offre.
#
# La séparation est INVISIBLE pour les appelants : `charger` réinjecte le champ
# `description`, l'écriture le ressort. Aucun des 22 usages de `o["description"]`
# n'a eu besoin de changer.
DESCRIPTIONS = HERE / "descriptions.json"


def oid(offre):
    """Identifiant stable d'une offre : « entreprise|poste ».

    Unique sur les 2613 offres réelles (vérifié), et déjà la convention de l'app.
    Surtout PAS l'URL : elle change quand un doublon mieux classé la promeut.
    """
    return f"{(offre.get('entreprise') or '').strip()}|{(offre.get('poste') or '').strip()}"


def _lire_descriptions():
    try:
        return json.loads(DESCRIPTIONS.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def charger(chemin=None, descriptions=True):
    """Les offres, en LECTURE SEULE, descriptions réinjectées.

    Pas de verrou : les écritures étant atomiques (tmp + os.replace), une lecture
    ne voit jamais un fichier à moitié écrit. Ne pas utiliser si l'on compte
    réécrire — voir `transaction`.

    `descriptions=False` évite de lire le fichier annexe quand on n'en a pas
    besoin : c'est là qu'est le gain de temps.
    """
    p = Path(chemin or CHEMIN)
    try:
        offres = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    if descriptions and p == CHEMIN:
        textes = _lire_descriptions()
        if textes:
            for o in offres:
                if not (o.get("description") or "").strip():
                    t = textes.get(oid(o))
                    if t:
                        o["description"] = t
    return offres


def sauver(offres, chemin=None, _avant=None):
    """Écriture atomique, SANS verrou. Réservé aux cas où l'appelant tient déjà
    le verrou. Dans le doute, utiliser `transaction`.

    `_avant` : les descriptions déjà lues par l'appelant. `transaction` les
    transmet — sans ça, `sauver` relisait les 8,8 Mo que `charger` venait de
    lire, 63 ms jetés à chaque écriture.
    """
    p = Path(chemin or CHEMIN)
    if p != CHEMIN:                       # fichier de test : pas de separation
        jutil.jwrite(p, offres, _brut=True)
        return

    # ORDRE VOLONTAIRE : les descriptions D'ABORD. Si le processus meurt entre
    # les deux ecritures, le fichier annexe contient des entrees orphelines —
    # inoffensives — alors que l'inverse perdrait des descriptions.
    avant = _lire_descriptions() if _avant is None else _avant
    textes = dict(avant)
    vivants = set()
    for o in offres:
        cle_o = oid(o)
        vivants.add(cle_o)
        t = (o.pop("description", "") or "").strip()
        if t:
            textes[cle_o] = t
    if _avant is None or avant:
        # purge des orphelines. Sautee quand l'appelant n'a pas lu le fichier
        # annexe (transaction descriptions=False) : on ne saurait pas distinguer
        # « orpheline » de « pas chargee », et on effacerait tout.
        textes = {k: v for k, v in textes.items() if k in vivants}

    # N'ECRIRE QUE CE QUI A CHANGE. Reecrire systematiquement les 8,8 Mo de
    # descriptions coutait 230 ms a chaque transaction — plus cher que l'ancien
    # fichier unique. Or la quasi-totalite des ecritures ne touche AUCUNE
    # description : elles changent un fit, un statut, une URL.
    if textes != avant:
        jutil.jwrite(DESCRIPTIONS, textes)
    jutil.jwrite(p, offres, _brut=True)
    for o in offres:                      # l'appelant garde son objet complet
        t = textes.get(oid(o))
        if t:
            o["description"] = t


class VerrouIndisponible(RuntimeError):
    """Un autre programme modifie la file et ne l'a pas relâchée à temps."""


@contextmanager
def transaction(chemin=None, attente=180, relire=True, descriptions=True):
    """Verrou + relecture fraîche + écriture atomique à la sortie du bloc.

    `relire` : relit le disque À L'INTÉRIEUR du verrou. C'est le point essentiel.
    Charger la file puis prendre le verrou laisse une fenêtre pendant laquelle un
    autre programme écrit — on repartirait alors d'un état périmé et on
    effacerait son travail.

    Une exception dans le bloc ANNULE l'écriture : mieux vaut ne rien écrire
    qu'écrire un état à moitié transformé.

    `descriptions=False` : ne lit PAS le fichier annexe (8,8 Mo, 63 ms) et le
    laisse tel quel. C'est là qu'est le gain de vitesse — pour les programmes qui
    changent un fit, un statut ou une URL sans toucher au texte des annonces.
    Les offres n'auront alors pas de champ `description`, et les descriptions
    orphelines ne sont pas purgées : c'est le travail d'une écriture complète.
    """
    p = Path(chemin or CHEMIN)
    if not jutil.prendre_verrou(p, attente=attente):
        raise VerrouIndisponible(
            f"{p.name} est modifié par un autre programme (attente {attente}s dépassée)")
    try:
        # Une seule lecture des descriptions pour toute la transaction : elle
        # sert a les reinjecter en entree, PUIS a savoir en sortie si elles ont
        # change. Les relire dans sauver coutait 63 ms pour rien.
        textes = _lire_descriptions() if (relire and descriptions and p == CHEMIN) else {}
        offres = charger(p, descriptions=False) if relire else []
        if textes:
            for o in offres:
                if not (o.get("description") or "").strip():
                    t = textes.get(oid(o))
                    if t:
                        o["description"] = t
        yield offres
        sauver(offres, p, _avant=textes)  # atteint seulement si le bloc n'a pas levé
    finally:
        jutil.rendre_verrou(p)


def modifier(fn, chemin=None, attente=180):
    """`fn(offres)` sous verrou. Renvoie ce que `fn` renvoie.

    Sucre pour les programmes qui n'ont qu'une transformation à appliquer :

        n = modifier(lambda offres: sum(1 for o in offres if o.pop("vieux", None)))
    """
    with transaction(chemin, attente=attente) as offres:
        return fn(offres)


if __name__ == "__main__":
    q = charger()
    print(f"{len(q)} offres dans {CHEMIN.name}")
