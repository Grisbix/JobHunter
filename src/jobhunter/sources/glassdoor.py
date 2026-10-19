"""Glassdoor : la page de recherche, page 1.

Partie de jobhunter.sources (ancien Scripts/job_sources.py, phase 3.4)."""

import re
import time
from typing import Any

from jobhunter import journal as _journal
from jobhunter.sources import commun as _commun
from jobhunter.sources.commun import INCIDENTS, _lire_borne, _mk, contrat_du_titre, title_ok
from jobhunter.sources.indeed import INDEED_UA, _IndeedBride

_log = _journal.journal(__name__)


# ═══════════════ Glassdoor — la page de recherche, page 1 ═══════════════
# Meme demarche qu'Indeed, meme frontiere, resultat plus maigre.
#
#   /Emploi/…SRCH_….htm   AUTORISE. Le robots.txt ne ferme que les formes
#                         PAGINEES (« Disallow: /Emploi/*_IP* »), pas la
#                         premiere page.
#   /graph                INTERDIT — « Disallow: /graph », ligne 145. C'est
#                         l'API GraphQL qu'utilise JobSpy. Son jeton, lui, est
#                         servi a tout visiteur dans le HTML (leur
#                         _get_csrf_token le lit sur une page publique), donc
#                         ce n'est pas un identifiant vole comme la cle iOS
#                         d'Indeed — mais le chemin est explicitement interdit
#                         aux robots, et cela suffit a le fermer.
#   pages 2 et +          « Disallow: /Emploi/*_IP* » : c'est la pagination.
#                         30 cartes par requete, et on s'arrete la.
#
# CE QUE GLASSDOOR DONNE, ET CE QU'IL NE DONNE PAS. Le ld+json de la page ne
# porte que le titre et l'URL. Tout le reste est dans le HTML rendu, repere par
# des attributs `data-test` (stables) et des classes CSS hachees (qui changent
# a chaque deploiement) : on n'accroche donc que les data-test et des PREFIXES
# de classe. Surtout, Glassdoor ne publie AUCUN type de contrat structure, la
# ou Indeed en fournit un sur 15 cartes sur 15. Le contrat retombe sur la
# lecture du titre, avec ses trous connus. L'anciennete est relative (« 30j+ »,
# « 3j »), pas une date : on ne la convertit que lorsqu'elle est bornee.
GD_HOTE = "https://www.glassdoor.fr"

GD_PAUSE = 12

GD_REPOS = 45

GD_ABANDON = 6

GD_LOC_FRANCE = 86  # locId du pays ; Glassdoor n'expose les id de VILLE

# que par /ajax/, interdit. On cherche donc France
# entiere et on trie ensuite avec zones.zone_lieu().
GD_UA = dict(INDEED_UA)

# Une carte commence a son intitule. Le nom de l'employeur est AVANT dans le
# HTML, le lieu et le salaire APRES : on decoupe donc sur les intitules et on
# lit de part et d'autre.
_RX_GD_TITRE = re.compile(r'<a\b[^>]*data-test="job-title"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S)

_RX_GD_EMPLOYEUR = re.compile(r'compactEmployerName[^"]*"[^>]*>(.*?)</span>', re.S)

_RX_GD_LIEU = re.compile(r'data-test="emp-location"[^>]*>(.*?)</div>', re.S)

_RX_GD_SALAIRE = re.compile(r'data-test="detailSalary"[^>]*>(.*?)</div>', re.S)

_RX_GD_AGE = re.compile(r'data-test="job-age"[^>]*>(.*?)</div>', re.S)

_RX_GD_EXTRAIT = re.compile(r'jobDescriptionSnippet[^"]*"[^>]*>(.*?)</div>', re.S)


def _gd_texte(h: str) -> str:
    """Fragment HTML → texte nu."""
    import html as _h

    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", _h.unescape(h or ""))).strip()


def _gd_date(age: Any) -> str:
    """« 3j » → la date d'il y a trois jours. « 30j+ » → rien.

    L'anciennete affichee est relative et parfois NON BORNEE : « 30j+ » couvre
    aussi bien 31 jours que huit mois. La convertir donnerait une date fausse
    dans la colonne meme qui sert a juger de la fraicheur — on prefere le vide.
    """
    a = (age or "").strip().lower()
    if "+" in a:
        return ""
    m = re.match(r"^(\d+)\s*(h|j|d|min)", a)
    if not m:
        return ""
    n = int(m.group(1))
    jours = n if m.group(2) in ("j", "d") else 0
    return time.strftime("%Y-%m-%d", time.localtime(time.time() - jours * 86400))


def _gd_url(mot: str) -> str:
    """L'URL canonique de recherche. Le mot-cle est DANS le chemin.

    Piege verifie a la main : `?sc.keyword=analyste+financier` est ignore en
    silence. La page repond 200, sert 30 cartes bien formees — et parle de
    « Vendeur Projets » et d'« Aide familial(e) ». Le mot-cle reel est celui
    que designent les offsets du nom de fichier :

        france-analyste-esg-emplois-SRCH_IL.0,6_IN86_KO7,19.htm
                                         ^^^^^      ^^^^^^
        IL.0,6  le LIEU occupe les caracteres 0 a 6 du slug  → « france »
        IN86    l'identifiant de pays
        KO7,19  le MOT-CLE occupe les caracteres 7 a 19      → « analyste-esg »

    Se tromper ici ne casse rien : ca remplit la file de commerciaux. C'est
    pire qu'une erreur, c'est une erreur invisible.
    """
    import unicodedata

    n = unicodedata.normalize("NFD", mot.lower())
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    n = re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", n)).strip("-")
    debut = len("france-")
    return (
        f"{GD_HOTE}/Emploi/france-{n}-emplois"
        f"-SRCH_IL.0,6_IN{GD_LOC_FRANCE}_KO{debut},{debut + len(n)}.htm"
    )


def _gd_cartes(mot: str) -> list[Any]:
    """Les cartes de la page 1 pour un mot-cle, France entiere."""
    import urllib.error
    import urllib.request

    url = _gd_url(mot)
    texte = ""
    for essai in (1, 2):
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=GD_UA), timeout=25
            ) as f:
                texte = _lire_borne(f).decode("utf-8", "replace")
            break
        except urllib.error.HTTPError as e:
            # Un 403 n'a PAS de seconde chance : c'est un refus d'entree, pas
            # une limite de debit. Le 2026-10-07, le repos de 45 s puis la
            # nouvelle tentative ont ete payes sur chacun des 37 mots-cles
            # atteints, et l'etape a ete tuee a 40 min (idem le 2026-10-03).
            if e.code == 429 and essai == 1:
                attente = int(e.headers.get("Retry-After") or GD_REPOS)
                _log.info(f"    ~ {mot} : HTTP {e.code}, repos {attente} s")
                time.sleep(min(attente, 300))
                continue
            _log.info(f"    ! {mot} : HTTP {e.code}")
            INCIDENTS["glassdoor"][f"HTTP {e.code}"] += 1
            if e.code in (403, 429):
                raise _IndeedBride(e.code)
            return []
        except Exception as e:
            _log.info(f"    ! {mot} : {type(e).__name__}")
            return []

    return _gd_parse(texte)


def _gd_parse(texte: str) -> list[Any]:
    """HTML de la page de recherche → cartes. Separe du reseau pour etre
    testable sur une page enregistree, sans requete."""
    titres = list(_RX_GD_TITRE.finditer(texte))
    cartes = []
    for n, m in enumerate(titres):
        avant = texte[(titres[n - 1].end() if n else 0) : m.start()]
        apres = texte[m.end() : (titres[n + 1].start() if n + 1 < len(titres) else len(texte))]
        emp = _RX_GD_EMPLOYEUR.findall(avant)
        lieu = _RX_GD_LIEU.search(apres)
        sal = _RX_GD_SALAIRE.search(apres)
        age = _RX_GD_AGE.search(apres)
        ext = _RX_GD_EXTRAIT.search(apres)
        cartes.append(
            {
                "url": m.group(1),
                "titre": _gd_texte(m.group(2)),
                # Le dernier nom trouve AVANT l'intitule est celui de cette carte :
                # les precedents appartiennent aux cartes d'avant.
                "entreprise": _gd_texte(emp[-1]) if emp else "",
                "lieu": _gd_texte(lieu.group(1)) if lieu else "",
                "salaire": _gd_texte(sal.group(1)) if sal else "",
                "age": _gd_texte(age.group(1)) if age else "",
                "extrait": _gd_texte(ext.group(1)) if ext else "",
            }
        )
    return cartes


def scan_glassdoor(
    mots: list[str] | None = None, pause: float | None = None
) -> list[dict[str, Any]]:
    """Page 1 de la recherche Glassdoor, France entiere, un passage par mot-cle.

    30 cartes au maximum par requete. La zone est jugee apres coup sur le lieu
    de la carte, faute de pouvoir cibler une ville : les identifiants de ville
    ne s'obtiennent que par /ajax/, interdit aux robots.
    """
    mots = mots or _commun.KEYWORDS
    pause = GD_PAUSE if pause is None else pause
    _EX = _commun.contrats_exclus()
    offers: list[dict[str, Any]] = []
    vus: set[str] = set()
    refus = refuses = 0
    _log.info(
        f"  Glassdoor : {len(mots)} mots-cles ({pause} s entre chaque, "
        f"~{len(mots) * pause // 60} min)"
    )
    for i, mot in enumerate(mots):
        if i:
            time.sleep(pause)
        try:
            cartes = _gd_cartes(mot)
            refus = 0
        except _IndeedBride as e:
            refuses += 1
            # REFUS D'ENTREE : on s'arrete au premier. Un seul 403 suffit parce
            # qu'il n'est jamais isole — le 2026-10-07, 37 mots sur 37 l'ont
            # recu, la nouvelle tentative ne passant que 7 fois — et
            # que chaque requete de plus prolonge la mise a l'ecart. Le cout
            # d'un 403 fortuit : les mots restants de Glassdoor, pour un jour.
            if e.args and e.args[0] == 403:
                _log.warning(
                    f"  ⏸ Glassdoor : refus d'entree (HTTP 403) — source fermee "
                    f"pour aujourd'hui, pas d'insistance, {len(offers)} offres "
                    f"conservees"
                )
                break
            refus += 1
            if refus >= GD_ABANDON:
                _log.warning(
                    f"  ⏸ Glassdoor : {refus} refus d'affilee (HTTP {e}) — passe "
                    f"arretee, {len(offers)} offres conservees"
                )
                break
            # Refus EN ALTERNANCE avec des succes : le compteur d'affilee se
            # remettait a zero, et chaque mot payait 45 s de repos. Le
            # 2026-10-07, la passe a ete coupee a 40 min par la minuterie, et WTJ,
            # qui passe apres, n'a rien collecte.
            if refuses >= 2 * GD_ABANDON:
                _log.warning(
                    f"  ⏸ Glassdoor : {refuses} refus sur {i + 1} mots-cles — passe "
                    f"arretee, {len(offers)} offres conservees"
                )
                break
            continue
        for c in cartes:
            u = c["url"].split("?")[0]
            if not u or u in vus:
                continue
            vus.add(u)
            titre = c["titre"]
            if not titre or not title_ok(titre):
                continue
            # Glassdoor ne publie pas de type de contrat : le titre est tout ce
            # qu'on a, et il se tait une fois sur deux. C'est le recul principal
            # par rapport a Indeed, il vaut mieux l'ecrire que le decouvrir.
            ctr = contrat_du_titre(titre)
            if ctr in _EX:
                continue
            o = _mk(
                titre,
                c["url"],
                c["entreprise"] or "Glassdoor",
                c["lieu"],
                _gd_date(c["age"]),
                "glassdoor",
                c["extrait"],
            )
            o["contrat"] = ctr
            o["salaire"] = c["salaire"]
            o["desc_partielle"] = True
            offers.append(o)
    _log.warning(
        f"  ✓ Glassdoor → {len(offers)} offres ({refuses} requetes refusees) — "
        f"description = extrait, pas de contrat structure"
    )
    return offers
