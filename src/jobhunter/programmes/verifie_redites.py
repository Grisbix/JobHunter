#!/usr/bin/env python3
"""verifie_redites.py — Cherche les repetitions dans les lettres generees.

POURQUOI. Les defauts de redite se voient a la lecture, jamais a l'ecriture du
generateur : chaque morceau est correct isolement, c'est leur assemblage qui
begaie. Trois exemples releves a la main sur une seule lettre :

    « la trésorerie et le financement, l'analyse financière, la modélisation
      financière et le contrôle de gestion, et je pratique… »   trois « et »
    « l'analyse financière, la modélisation financière »         meme fin
    « Ma formation correspond…, et j'y ajoute…, et une bonne… »  deux « et »

Relire une lettre a la main les trouve. Relire 3900 lettres, non. Ce programme
les compte.

CE QU'IL SIGNALE :
  - une phrase qui porte deux « et » (ou « and ») ou plus ;
  - deux elements d'enumeration qui finissent par le meme mot ;
  - un mot de contenu employe trois fois ou plus dans le corps.

Il ne corrige rien : il rend la liste, a corriger dans tailor_application.py.

Run :
  python verifie_redites.py                    # 40 lettres au hasard
  python verifie_redites.py --toutes
  python verifie_redites.py --fichier "Lettres/Par_offre/xxx.docx"
"""

import argparse
import collections
import html
import importlib
import random
import re
import sys
import zipfile
from pathlib import Path

from jobhunter import racine as _racine

HERE = _racine.scripts()
ROOT = HERE.parent

from jobhunter import chemins

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Mots vides et formules de politesse : leur repetition ne dit rien.
_BANALS = {
    "votre",
    "notre",
    "leurs",
    "comme",
    "depuis",
    "serais",
    "heureux",
    "sein",
    "equipes",
    "équipes",
    "parcours",
    "monsieur",
    "madame",
    "salutations",
    "distinguees",
    "distinguées",
    "expression",
    "disposition",
    "entretien",
    "poste",
    "annonce",
    "vous",
    "avec",
    "dans",
    "pour",
    "mais",
    "plus",
    "cette",
    "sont",
    "suis",
    "elles",
} | {m.lower() for m in importlib.import_module("jobhunter.profil").identite()["nom"].split()}


def texte(chemin):
    """Le texte affiche d'un .docx, paragraphes separes."""
    x = zipfile.ZipFile(chemin).read("word/document.xml").decode("utf-8", "replace")
    x = re.sub(r"</w:p>", "\n", x)
    return html.unescape(re.sub(r"<[^>]+>", "", x)).strip()


# La formule d'appel, quelle qu'elle soit. Ce reperage cherchait « Madame, »
# ou « Dear  » en debut de ligne, ce qui couvrait les deux seules formules que
# la lettre savait ecrire. Depuis qu'elle nomme le recruteur, elle ouvre sur
# « Monsieur Mac Arthur, » ou « Madame Moussa, Madame Girard, » — et l'en-tete
# n'etait plus coupe du tout. Le nom, le courriel, le telephone et l'objet
# entraient alors dans le comptage : la lettre Mirova s'est vu reprocher
# « 2 conjonctions » dans un bloc qui commencait par son propre nom.
#
# On reconnait donc une LIGNE COURTE finissant par une virgule, ce qu'aucune
# ligne d'en-tete ne fait et ce que toute formule d'appel fait.
_RX_APPEL = re.compile(r"^(?:Madame|Monsieur|Mesdames|Messieurs|Bonjour|Dear)\b.{0,60},$")


def corps(t):
    """Le corps, sans l'en-tete (nom, courriel, telephone, date, objet)."""
    lignes = [l for l in t.split("\n") if l.strip()]
    for i, l in enumerate(lignes):
        if _RX_APPEL.match(l.strip()):
            return "\n".join(lignes[i + 1 :])
    return "\n".join(lignes)


def defauts(t):
    """La liste des redites d'une lettre. Vide = rien a signaler."""
    c = corps(t)
    trouves = []

    for ph in re.split(r"(?<=[.!?])\s+", c):
        n = len(re.findall(r"\b(?:et|and)\b", ph, re.I))
        if n >= 2:
            trouves.append(f"{n} conjonctions : {ph[:88]}…")

    # PAS DE POINT-VIRGULE. Demande de l'utilisateur, 2026-09-21. Il joint deux
    # propositions que le point separe mieux : la seconde se lit seule, et une
    # lettre de candidature gagne a etre faite de phrases courtes. Dans une
    # enumeration de CV, il fait le travail du «  ·  » que ces documents
    # emploient deja ailleurs — un seul separateur vaut mieux que deux.
    for m in re.finditer(r"[^.!?]*;[^.!?]*", c):
        trouves.append(f"point-virgule : {m.group(0).strip()[:82]}…")

    # Elements d'enumeration : on decoupe sur les virgules ET sur la
    # conjonction finale, sinon « l'analyse financière et la modélisation
    # financière » compte pour un seul element et la repetition passe.
    for ph in re.split(r"(?<=[.!?])\s+", c):
        elems = [e.strip() for e in re.split(r",|\bet\b|\band\b", ph) if e.strip()]
        fins = [e.rsplit(" ", 1)[-1].lower().strip(".:;") for e in elems if len(e.split()) >= 2]
        for mot, n in collections.Counter(fins).items():
            if n >= 2 and len(mot) >= 5 and mot not in _BANALS:
                trouves.append(f"« {mot} » finit {n} elements : {ph[:78]}…")

    # Les mots en MINUSCULE seulement. « Master en Finance », « Acme Finance »
    # et « corporate finance » comptaient pour trois repetitions du meme mot,
    # alors que les deux premiers sont des noms propres — un diplome et une
    # societe — qu'on ne peut ni renommer ni eviter. Ne restent que les mots
    # que la redaction choisit vraiment.
    mots = re.findall(r"\b[a-zà-ÿ]{5,}\b", c)
    for mot, n in collections.Counter(mots).items():
        if n >= 3 and mot not in _BANALS:
            trouves.append(f"« {mot} » revient {n} fois dans le corps")

    return trouves


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--toutes", action="store_true")
    ap.add_argument("--fichier")
    ap.add_argument("--echantillon", type=int, default=40)
    a = ap.parse_args()

    if a.fichier:
        cibles = [Path(a.fichier) if Path(a.fichier).is_absolute() else ROOT / a.fichier]
    else:
        toutes = sorted(chemins.LT_PAR_OFFRE.glob("*.docx"))
        toutes = [p for p in toutes if not p.name.startswith("~$")]
        cibles = toutes if a.toutes else random.sample(toutes, min(a.echantillon, len(toutes)))

    print(f"{len(cibles)} lettre(s) examinee(s)\n")
    compte = collections.Counter()
    sales = 0
    for p in cibles:
        try:
            d = defauts(texte(p))
        except Exception as e:
            print(f"  ! {p.name[:60]} : {type(e).__name__}")
            continue
        if not d:
            continue
        sales += 1
        if len(cibles) <= 5 or sales <= 6:
            print(f"── {p.name[:72]}")
            for x in d:
                print(f"     {x}")
        for x in d:
            compte[x.split(" :")[0].split(" revient")[0]] += 1

    print(f"\n{sales} lettre(s) avec au moins une redite sur {len(cibles)}")
    if compte:
        print("\nLes redites les plus frequentes :")
        for x, n in compte.most_common(10):
            print(f"  {n:4}  {x}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
