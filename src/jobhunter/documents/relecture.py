"""Relecture d'une lettre : une seconde passe qui signale, sans jamais réécrire.

Partie de jobhunter.documents. Le générateur assemble des morceaux corrects un à un ;
ce qui cloche se voit à la lecture de l'ensemble, confronté à l'annonce. Cette passe
part de zéro, sans le contexte de la rédaction, et rend une liste de remarques. C'est
l'utilisateur qui corrige (`Lettres/Sur_mesure/`).

Ce qu'elle cherche, en plus des redites de `verifie_redites` :
- le candidat qui se dévalorise (« encore court », « malgré », « je suis junior ») — la
  règle qui prime sur toutes — et son inverse, le superlatif creux ;
- « excellent » pour un niveau de langue (on écrit « courant » / « fluent ») ;
- tiret cadratin et barre oblique au fil du texte ;
- une autre entreprise que celle de l'offre nommée dans la lettre (copier-coller) ;
- un destinataire nommé que l'annonce ne nomme pas ;
- ce qu'une annonce piégée aurait pu glisser dans une lettre écrite par IA : consigne
  au modèle, adresse web ou courriel inconnus. L'annonce est une entrée non fiable.
- un gabarit non rempli.

Les motifs sont en français et en anglais. Une remarque est un indice, pas un verdict.
"""

import collections
import html
import re
import unicodedata
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from jobhunter.documents.controle import _RX_GABARIT  # le même motif que le contrôle


@dataclass(frozen=True)
class Remarque:
    """Un point à relire dans la lettre."""

    regle: str  # « dévalorisation », « superlatif », « langue », …
    extrait: str  # le passage concerné, court
    conseil: str


def _plat(texte: str) -> str:
    t = unicodedata.normalize("NFKD", texte.casefold()).encode("ascii", "ignore").decode()
    return " ".join(t.split())


def _extrait(texte: str, debut: int, fin: int, marge: int = 40) -> str:
    a, b = max(0, debut - marge), min(len(texte), fin + marge)
    return ("…" if a else "") + " ".join(texte[a:b].split()) + ("…" if b < len(texte) else "")


# (règle, motif, conseil). Motifs cherchés sur le texte tel quel, insensibles à la casse.
_MOTIFS: tuple[tuple[str, str, str], ...] = (
    (
        "dévalorisation",
        r"\b(?:court(?:e)? mais|encore (?:court|jeune|limit|peu)|malgr[ée] (?:mon|ma|mes|un|une)"
        r"|je (?:suis|reste) (?:encore )?junior|junior et je l.assume|sans d[ée]tour"
        r"|je ne cherche pas [àa] (?:masquer|cacher)|peu d.exp[ée]rience|manque d.exp[ée]rience"
        r"|m[eê]me si (?:mon|ma|je)|bien que (?:mon|ma|je)"
        r"|although (?:my|i)|limited experience|lack of experience|still (?:junior|new|early)"
        r"|despite my)",
        "On énonce ce qu'on apporte, jamais ce qui manque : supprimer la concessive, "
        "le paragraphe tient sans.",
    ),
    (
        "superlatif",
        r"\b(?:retenu toute mon attention|sp[ée]cialisation rare|se rencontrent rarement"
        r"|constitue ma sp[ée]cialit[ée]|le seul (?:sujet|candidat|profil)|parfaitement adapt"
        r"|profil id[ée]al|candidat id[ée]al|caught my (?:full )?attention|ideal candidate"
        r"|perfect (?:fit|match)|unique (?:profile|combination))",
        "Pas de superlatif ni de jugement sur le marché : prouver par un fait chiffré.",
    ),
    (
        "langue",
        r"\b(?:excellent(?:e)?s? (?:niveau d.)?(?:anglais|allemand|espagnol|italien|fran[çc]ais)"
        r"|(?:anglais|allemand|espagnol|italien) excellent|excellent (?:english|german|spanish"
        r"|french|italian)|(?:english|german|spanish|french) \(excellent\))",
        "Niveau de langue : « courant » (« fluent »), jamais « excellent ».",
    ),
    (
        "injection",
        r"\b(?:ignore (?:all |the )?(?:previous|above|prior)|instructions? (?:pr[ée]c[ée]dentes|"
        r"ci-dessus)|en tant qu.(?:ia|intelligence artificielle|assistant)|as an ai\b"
        r"|language model|mod[èe]le de langage|system prompt|prompt\b)",
        "Texte étranger à une lettre, sans doute venu de l'annonce : à retirer, et vérifier "
        "le reste de la lettre.",
    ),
)
_RX = tuple((r, re.compile(m, re.I), c) for r, m, c in _MOTIFS)
_RX_URL = re.compile(r"\bhttps?://\S+|\bwww\.\S+", re.I)
_RX_MAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# « Madame Dupont, » / « Dear Ms Smith, » : une civilité suivie d'un nom propre. La
# formule d'appel peut en nommer plusieurs (« Madame Martin, Madame Dupont, ») : chacun
# est cherché dans l'annonce, pas seulement le premier (audit Codex du 19/10).
_CIV = r"(?:Madame|Monsieur|(?:Dear )?(?:Mr|Mrs|Ms|Miss|Dr)\.?)"
_RX_APPEL = re.compile(_CIV + r"\s")
_RX_NOMME = re.compile(
    r"(?:^|(?<=, )|(?<= et )|(?<= and ))"
    + _CIV
    + r"\s+([A-ZÀ-Ý][\w'’-]+(?:\s+[A-ZÀ-Ý][\w'’-]+)*)(?=\s*,|\s+(?:et|and)\s)"
)


# ── Redites (ancien verifie_redites, déplacé en 2.13) ─────────────────────────

# Mots vides et formules de politesse : leur repetition ne dit rien.
_BANALS_BASE = {
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
}


def _banals() -> set[str]:
    """Les mots banals, plus le nom du candidat (lu à l'appel)."""
    try:
        from jobhunter.profil import identite

        nom = {m.lower() for m in identite()["nom"].split()}
    except Exception:  # profil absent : on compte sans son nom
        nom = set()
    return _BANALS_BASE | nom


def texte(chemin: Path | str) -> str:
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


def corps(t: str) -> str:
    """Le corps, sans l'en-tete (nom, courriel, telephone, date, objet)."""
    lignes = [l for l in t.split("\n") if l.strip()]
    for i, l in enumerate(lignes):
        if _RX_APPEL.match(l.strip()):
            return "\n".join(lignes[i + 1 :])
    return "\n".join(lignes)


def defauts(t: str) -> list[str]:
    """La liste des redites d'une lettre. Vide = rien a signaler."""
    c = corps(t)
    trouves: list[str] = []
    banals = _banals()

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
            if n >= 2 and len(mot) >= 5 and mot not in banals:
                trouves.append(f"« {mot} » finit {n} elements : {ph[:78]}…")

    # Les mots en MINUSCULE seulement. « Master en Finance », « Acme Finance »
    # et « corporate finance » comptaient pour trois repetitions du meme mot,
    # alors que les deux premiers sont des noms propres — un diplome et une
    # societe — qu'on ne peut ni renommer ni eviter. Ne restent que les mots
    # que la redaction choisit vraiment.
    mots = re.findall(r"\b[a-zà-ÿ]{5,}\b", c)
    for mot, n in collections.Counter(mots).items():
        if n >= 3 and mot not in banals:
            trouves.append(f"« {mot} » revient {n} fois dans le corps")

    return trouves


def relire(
    lettre: str,
    entreprise: str = "",
    annonce: str = "",
    autres_entreprises: Iterable[str] = (),
    connus: Iterable[str] = (),
) -> list[Remarque]:
    """Les remarques sur une lettre ; vide = rien à signaler.

    Args:
        lettre: le texte de la lettre (en-tête compris : il est écarté ici).
        entreprise: l'entreprise de l'offre.
        annonce: le texte de l'annonce (pour le nom du destinataire).
        autres_entreprises: les autres entreprises de la file ; une seule nommée dans la
            lettre trahit un copier-coller.
        connus: adresses web et courriels légitimes (ceux du profil, de l'entreprise).
    """
    le_corps = corps(lettre)
    sortie: list[Remarque] = []
    for regle, rx, conseil in _RX:
        for m in rx.finditer(le_corps):
            sortie.append(Remarque(regle, _extrait(le_corps, m.start(), m.end()), conseil))
    for m in _RX_GABARIT.finditer(lettre):
        sortie.append(
            Remarque("gabarit", _extrait(lettre, m.start(), m.end()), "Champ non rempli.")
        )

    # Ponctuation de la règle mécanique : tiret cadratin, barre oblique hors adresses.
    sans_liens = _RX_URL.sub(" ", le_corps)
    for m in re.finditer(r"—|(?<![\d\s])/(?![\d\s])", sans_liens):
        sortie.append(
            Remarque(
                "ponctuation",
                _extrait(sans_liens, m.start(), m.end(), 25),
                "Ni tiret cadratin ni barre oblique au fil du texte.",
            )
        )
    for d in defauts(lettre):
        sortie.append(Remarque("redite", d, "Une conjonction par phrase, aucun mot trois fois."))

    # Adresses que rien n'explique : la signature et l'entreprise sont « connues ».
    connus = [c for c in connus if c]
    for rx in (_RX_URL, _RX_MAIL):
        for m in rx.finditer(le_corps):
            if not _legitime(m.group(0), connus):
                sortie.append(
                    Remarque(
                        "injection",
                        m.group(0),
                        "Adresse inconnue dans le corps : d'où vient-elle ? Une annonce "
                        "piégée peut en glisser une dans une lettre écrite par IA.",
                    )
                )

    # Copier-coller : une autre entreprise de la file nommée dans le corps.
    mien = _plat(entreprise)
    texte_plat = f" {_plat(le_corps)} "
    for autre in {a for a in autres_entreprises if a}:
        p = _plat(autre)
        if len(p) < 4 or p == mien or (mien and (p in mien or mien in p)):
            continue
        if re.search(r"(?<![a-z0-9])" + re.escape(p) + r"(?![a-z0-9])", texte_plat):
            sortie.append(
                Remarque(
                    "entreprise",
                    autre,
                    f"La lettre nomme « {autre} », pas « {entreprise} » : reste d'une autre "
                    "candidature ?",
                )
            )

    # Destinataire nommé : seulement si l'annonce le nomme.
    if annonce:
        from jobhunter.documents.message import nom_dans_offre

        for ligne in lettre.splitlines():
            if not _RX_APPEL.match(ligne.strip()):
                continue
            for m in _RX_NOMME.finditer(ligne.strip()):
                if not nom_dans_offre(m.group(1), annonce):
                    sortie.append(
                        Remarque(
                            "destinataire",
                            m.group(0) + ",",
                            "Nom absent du texte de l'annonce : « Madame, Monsieur, » / "
                            "« Dear Sir or Madam, ».",
                        )
                    )
    return sortie


def _hote_chemin(adresse: str) -> tuple[str, str]:
    """« https://www.Acme.fr/a/b?x » → (« acme.fr », « /a/b ») ; un courriel → (domaine, « @local »)."""
    from urllib.parse import urlsplit

    a = adresse.strip().rstrip(".,;)").casefold()
    if "@" in a and "://" not in a:
        local, _, domaine = a.rpartition("@")
        return domaine, "@" + local
    p = urlsplit(a if "://" in a else "http://" + a)
    hote = (p.hostname or "").removeprefix("www.")
    return hote, p.path.rstrip("/")


def _legitime(trouve: str, connus: Iterable[str]) -> bool:
    """L'adresse trouvée dans la lettre est-elle l'une des connues ?

    Les hôtes se comparent entiers, à une frontière de point : « jobs.acme.fr » va avec
    « acme.fr », mais « acme.fr.evil.test » et « evil.test/acme.fr » non (audit Codex du
    19/10 : la comparaison par sous-chaîne les laissait passer). Un connu qui porte un
    chemin (un profil LinkedIn) n'admet que ce chemin et ce qui le prolonge ; un courriel
    connu n'admet que lui-même.
    """
    hote, chemin = _hote_chemin(trouve)
    if not hote or "." not in hote:
        return False
    for c in connus:
        if not c:
            continue
        kh, kc = _hote_chemin(c)
        if not kh:
            continue
        if kc.startswith("@") or chemin.startswith("@"):
            if (kh, kc) == (hote, chemin):
                return True
            # Un courriel au domaine d'un site connu (rh@acme.fr pour acme.fr).
            if chemin.startswith("@") and not kc and (hote == kh or hote.endswith("." + kh)):
                return True
            continue
        meme_site = hote == kh or hote.endswith("." + kh) or kh.endswith("." + hote)
        if meme_site and (not kc or chemin == kc or chemin.startswith(kc + "/")):
            return True
    return False
