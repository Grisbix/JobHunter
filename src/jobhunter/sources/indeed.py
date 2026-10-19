"""Indeed : la page de resultats, et rien d'autre.

Partie de jobhunter.sources (ancien Scripts/job_sources.py, phase 3.4).
"""

import json
import re
import sys
import time
from typing import Any, NoReturn
from urllib.parse import quote

from jobhunter import journal as _journal
from jobhunter import paresseux as _paresseux
from jobhunter.reseau import exiger_http
from jobhunter.scoring import zones as _zones
from jobhunter.sources import commun as _commun
from jobhunter.sources.commun import (
    HERE,
    INCIDENTS,
    _lire_borne,
    _mk,
    _strip_html,
    contrat_du_titre,
    title_ok,
)

_log = _journal.journal(__name__)


_ici = sys.modules[__name__]
# Valeurs tirees du profil : calculees a la premiere lecture, pas a l'import
# (jobhunter.paresseux). Dans ce module, on les lit par `_ici.NOM`.
_PARESSEUX: _paresseux.Fabriques = {}


def __getattr__(nom: str) -> Any:
    return _paresseux.lire(_ici, _PARESSEUX, nom)


# ═══════════════ Indeed — la PAGE DE RÉSULTATS, et rien d'autre ═══════════════
# Ce qu'on lit et ce qu'on ne lit pas. La frontiere n'est pas technique, elle
# est deliberee, et elle merite d'etre ecrite noir sur blanc :
#
#   /jobs?q=…&l=…   AUTORISE. Le bloc « User-agent: * » du robots.txt commence
#                   par « Allow: / » ; sur ses 468 lignes de Disallow, aucune ne
#                   vise la recherche. Seuls les chemins PAYS sont fermes
#                   (/jobs/FR/, /jobs/CA/…), ce qui n'est pas la meme URL.
#   /viewjob?jk=…   INTERDIT — « Disallow: /viewjob? », ligne 170. On ne va
#                   JAMAIS la chercher. L'URL est stockee pour que l'utilisateur
#                   l'ouvre lui-meme dans son navigateur : stocker un lien
#                   n'est pas le crawler.
#   page 2 et +     &start=10 repond 307 vers secure.indeed.com/auth, avec
#                   « branding=page-two-signin ». C'est un mur de CONNEXION,
#                   pas un anti-bot. On s'arrete a la page 1, soit 15 cartes
#                   par requete, et le volume vient du nombre de requetes.
#
# L'API mobile apis.indeed.com/graphql sert tout cela sans aucune de ces
# limites — description entiere comprise. Elle exige une cle extraite de
# l'application iOS d'Indeed (c'est ce que fait JobSpy, 4300 etoiles). Cette
# cle n'est pas la notre : on ne s'en sert pas. Ce n'est pas une impossibilite
# technique, c'est un choix, et c'est le seul ecart entre eux et nous.
#
# CONSEQUENCE DE CONCEPTION. Indeed est une source de DECOUVERTE, pas de
# dossier. Le snippet fait 140 a 165 caracteres la ou fit_score travaille sur
# l'annonce entiere. rang_source la classe 1 (agregateur) : des qu'une autre
# source publie la meme annonce, son lien reprend la place. Ce qu'Indeed
# apporte et que les autres nous donnent mal, c'est le CADRE — type de contrat
# (15/15 des cartes mesurees), date de publication REELLE, teletravail,
# salaire. Trois champs ou la file est aujourd'hui presque vide.
INDEED_HOTE = "https://fr.indeed.com"

# Aucun crawl-delay annonce dans le robots.txt, mais un bridage bien reel — et
# qui ne repond PAS a la cadence. Mesure, six requetes identiques a chaque fois :
#
#   pause 15 s :  403 403 403 200 200 200   → 3 refus
#   pause 25 s :  200 403 403 403 403 403   → 5 refus
#
# Ralentir n'ameliore rien : ce n'est pas un debit, c'est un quota glissant par
# adresse, qui se remplit et se vide. Aucun en-tete Retry-After.
#
# LE QUOTA SE VIDE POUR LA JOURNEE, PAS POUR LA MINUTE. Journal de la journee
# du 17/09, meme machine :
#
#   1re passe, 28 requetes   → 61 offres, environ la moitie refusee
#   2e passe (16 requetes)   → 2 reponses, 14 refus
#   3e passe, 110 requetes   → 0 offre, abandon des la 6e requete
#
# Entre la 2e et la 3e, deux heures d'attente n'ont rien rempli. Tirer sur un
# quota vide ne fait que le garder vide, et chaque refus coute 45 s de repos
# plus deux requetes.
#
# D'OU LE BUDGET. Une passe s'arrete a INDEED_BUDGET requetes, et elle ne
# reprend pas les memes mots-cles : elle repart la ou la precedente s'est
# arretee. 55 mots-cles x 2 villes = 110 couples, soit environ cinq jours pour
# faire le tour — ce qui convient a des offres qui vivent plusieurs semaines.
INDEED_PAUSE = 12  # assez pour ne pas peser, inutile d'aller plus lent

INDEED_BUDGET = 20  # requetes par passe ; au-dela le quota est a sec

INDEED_ETAT = HERE / ".indeed_rotation"  # ou la passe precedente s'est arretee

INDEED_REPOS = 45  # repos apres un refus, avant la seule seconde chance

# Depuis le 04/10 : refus 403/challenge = arrêt immédiat ; quota 429 = un
# réessai borné, puis arrêt. Le challenge Cloudflare a été observé en réel.
# Lieux de recherche : les secteurs prioritaires du profil (zones.py).
_PARESSEUX["INDEED_LIEUX"] = lambda: (
    [s["libelle"] for s in _zones.SECTEURS_PRIORITAIRES] or ["France"]
)

# On se presente pour ce qu'on est. Mesure faite, les trois cas :
#   « JobHunter/1.0 … »   → 200, 1 108 971 o
#   aucun UA (Python-urllib) → 403
#   un UA Chrome          → 200
# Indeed refuse l'agent par DEFAUT de la bibliotheque, pas les robots : un nom
# franc suffit. Inutile de se deguiser en navigateur, on ne le fait donc pas.
INDEED_UA = {
    "User-Agent": "JobHunter/1.0 (recherche d'emploi personnelle)",
    "Accept-Language": "fr-FR,fr;q=0.9",
}

_RX_INDEED_BLOB = re.compile(r'providerData\["mosaic-provider-jobcards"\]\s*=\s*')

# « Temps plein » et « Temps partiel » sont des temps de travail, pas des
# contrats : les laisser passer remplirait la colonne `contrat` de valeurs qui
# ne servent a rien pour filtrer. Ils sont ignores, et une carte qui ne porte
# qu'eux repart sans contrat — « non precise » reste une reponse honnete.
_INDEED_CONTRAT = {
    "cdi": "CDI",
    "cdd": "CDD",
    "stage": "Stage",
    "alternance": "Alternance",
    "apprentissage": "Alternance",
    "freelance": "Freelance",
    "independant": "Freelance",
    "interim": "Interim",
    "temporaire": "Interim",
}


class _IndeedBride(Exception):
    """Indeed bride apres une seconde chance.

    On arrete la passe et on GARDE ce qui a ete lu : une passe interrompue vaut mieux
    qu'une passe perdue, et le scan suivant reprendra les mots-cles restants.
    """


def _json_objet(texte: str, depart: int) -> str:
    r"""L'objet JSON complet qui commence a l'accolade `depart`.

    Une expression non gourmande (\\{.*?\\};) s'arreterait au premier « }; »
    rencontre, y compris a l'interieur d'une chaine. Le blob d'Indeed fait 54 ko
    et contient du HTML de description : on compte les accolades en sautant ce
    qui est entre guillemets.
    """
    prof = 0
    chaine = False
    echap = False
    for i in range(depart, len(texte)):
        c = texte[i]
        if chaine:
            if echap:
                echap = False
            elif c == "\\":
                echap = True
            elif c == '"':
                chaine = False
            continue
        if c == '"':
            chaine = True
        elif c == "{":
            prof += 1
        elif c == "}":
            prof -= 1
            if prof == 0:
                return texte[depart : i + 1]
    return ""


class _IndeedBloque(Exception):
    """Refus explicite, connexion requise ou réponse inexploitable : arrêt."""


INDEED_REQUETES = 0


def _indeed_cartes(mot: str, lieu: str) -> list[Any]:
    """Lit la page publique ; distingue refus, quota et réponse vide valide."""
    import urllib.error
    import urllib.request
    from email.utils import parsedate_to_datetime

    global INDEED_REQUETES
    url = f"{INDEED_HOTE}/jobs?q={quote(mot)}&l={quote(lieu)}"

    def bloque(raison: str) -> NoReturn:
        INCIDENTS["indeed"][raison] += 1
        raise _IndeedBloque(raison)

    for essai in (1, 2):
        try:
            INDEED_REQUETES += 1
            with urllib.request.urlopen(  # nosec B310 : schéma vérifié par exiger_http
                urllib.request.Request(exiger_http(url), headers=INDEED_UA), timeout=25
            ) as f:
                if "secure.indeed.com" in f.geturl():
                    bloque("connexion requise")
                if f.headers.get("cf-mitigated", "").lower() == "challenge":
                    bloque("challenge anti-bot")
                texte = _lire_borne(f).decode("utf-8", "replace")
            break
        except _IndeedBloque:
            raise
        except urllib.error.HTTPError as e:
            code = e.code
            retry_after = e.headers.get("Retry-After") if e.headers else None
            e.close()
            if code in (401, 403):
                bloque(f"HTTP {code}")
            INCIDENTS["indeed"][f"HTTP {code}"] += 1
            if code != 429:
                raise _IndeedBloque(f"HTTP {code}")
            attente: float = INDEED_REPOS
            if retry_after:
                try:
                    attente = max(0, int(retry_after))
                except ValueError:
                    try:
                        attente = max(
                            0, parsedate_to_datetime(retry_after).timestamp() - time.time()
                        )
                    except (TypeError, ValueError, OverflowError):
                        pass
            # Ne jamais réessayer avant un Retry-After supérieur au budget.
            if essai == 2 or attente > 300:
                raise _IndeedBride(429)
            _log.warning(f"    ~ {mot} / {lieu} : HTTP 429, repos {attente:g} s")
            time.sleep(attente)
        except Exception as e:
            bloque(type(e).__name__)
    if re.search(r"<title[^>]*>[^<]*(?:security check|just a moment|captcha)", texte, re.I):
        bloque("challenge anti-bot")
    m = _RX_INDEED_BLOB.search(texte)
    if not m:
        bloque("format de page non reconnu")
    brut = _json_objet(texte, texte.find("{", m.end()))
    try:
        d = json.loads(brut)
        resultats: list[Any] = d["metaData"]["mosaicProviderJobCardsModel"]["results"]
        if not isinstance(resultats, list) or any(not isinstance(c, dict) for c in resultats):
            raise ValueError("results doit être une liste de cartes")
    except (ValueError, TypeError, KeyError):
        bloque("format des offres non reconnu")
    return resultats


def _indeed_contrat(job_types: Any) -> str:
    """['Temps plein', 'CDI'] → 'CDI'. Rien de reconnu → ''."""
    import unicodedata

    for t in job_types or []:
        n = unicodedata.normalize("NFD", str(t).lower())
        n = "".join(c for c in n if unicodedata.category(c) != "Mn").strip()
        if n in _INDEED_CONTRAT:
            return _INDEED_CONTRAT[n]
    return ""


def _indeed_date(ms: int) -> str:
    """Epoch en millisecondes → 'AAAA-MM-JJ'. C'est la VRAIE date de parution.

    Elle vaut mieux que la date de scan : la file porte 2634 offres datees du
    meme jour, celui ou on les a vues. Une valeur hors des bornes raisonnables
    est rejetee plutot que convertie en 1970.
    """
    try:
        s = float(ms) / 1000.0
    except Exception:
        return ""
    if not (946684800 < s < time.time() + 86400):  # entre 2000 et demain
        return ""
    return time.strftime("%Y-%m-%d", time.localtime(s))


def scan_indeed(
    mots: list[str] | None = None,
    lieux: list[str] | None = None,
    pause: float | None = None,
    *,
    persist: bool = True,
) -> list[dict[str, Any]]:
    """Page 1 des resultats Indeed, pour chaque couple (mot-cle, lieu).

    15 cartes au maximum par requete — c'est le mur de connexion de la page 2
    qui fixe ce plafond, pas nous. Le rendement vient donc du produit
    mots-cles x lieux.

    La passe ne traite qu'une TRANCHE de ce produit, INDEED_BUDGET couples, et
    reprend la ou la precedente s'est arretee. Le quota d'Indeed se vide pour
    la journee : une passe qui tente les 110 couples n'en obtient pas plus
    qu'une qui en tente 20, elle perd seulement une heure en repos inutiles.
    """
    mots = mots or _commun.KEYWORDS
    lieux = lieux or _ici.INDEED_LIEUX
    pause = INDEED_PAUSE if pause is None else pause
    _EX = _commun.contrats_exclus()
    offers = []
    vus = set()

    # Tous les couples, a plat : la rotation porte sur le COUPLE, pas sur le
    # mot-cle. Sinon une passe de 20 requetes couvrirait 10 mots-cles sur deux
    # villes, et la tranche suivante repartirait sur les memes villes.
    couples = [(m, l) for m in mots for l in lieux]
    depart = 0
    try:
        depart = int(INDEED_ETAT.read_text(encoding="utf-8").strip()) % len(couples)
    except Exception:
        pass
    tranche = [
        couples[(depart + i) % len(couples)] for i in range(min(INDEED_BUDGET, len(couples)))
    ]
    _log.info(
        f"  Indeed : {len(tranche)} couples sur {len(couples)} "
        f"(depuis le n° {depart + 1}, {pause} s entre chaque, "
        f"~{len(tranche) * pause // 60} min)"
    )

    fait = 0
    debut_http = INDEED_REQUETES
    bloque_raison = ""
    bride = False
    for mot, lieu in tranche:
        if fait:
            time.sleep(pause)
        fait += 1
        try:
            cartes = _indeed_cartes(mot, lieu)
        except _IndeedBloque as e:
            bloque_raison = str(e)
            _log.info(f"  Indeed : source indisponible ({e}) — arrêt sans réessai")
            break
        except _IndeedBride as e:
            bride = True
            _log.info(f"  Indeed : quota HTTP {e} — arrêt de la passe")
            break
        for c in cartes:
            jk = c.get("jobkey")
            if not jk or jk in vus:
                continue
            vus.add(jk)
            # Indeed marque lui-meme les annonces mortes. C'est
            # exactement ce que le controle de disponibilite va chercher,
            # offre par offre : ici c'est donne.
            if c.get("expired"):
                continue
            titre = (c.get("title") or c.get("displayTitle") or "").strip()
            if not titre or not title_ok(titre):
                continue
            ctr = _indeed_contrat(c.get("jobTypes"))
            if (ctr or contrat_du_titre(titre)) in _EX:
                continue
            o = _mk(
                titre,
                f"{INDEED_HOTE}/viewjob?jk={jk}",
                (c.get("company") or "").strip() or "Indeed",
                c.get("formattedLocation") or lieu,
                _indeed_date(c.get("pubDate")),
                "indeed",
                _strip_html(c.get("snippet") or ""),
            )
            o["contrat"] = ctr
            o["teletravail"] = (c.get("remoteWorkModel") or {}).get("text") or ""
            o["salaire"] = (c.get("salarySnippet") or {}).get("text") or ""
            # Le snippet n'est PAS l'annonce : 160 caracteres contre
            # plusieurs milliers. Sans ce drapeau, la promotion d'URL
            # ecraserait une description complete deja en file par ce
            # resume. Voir merge_into_queue.
            o["desc_partielle"] = True
            offers.append(o)
        if fait % 10 == 0:
            _log.info(f"    … {fait}/{len(tranche)} ({len(offers)} retenues)")

    # OU REPRENDRE DEMAIN. On avance de ce qui a ete REELLEMENT tente, pas du
    # budget : une passe arretee au 6e refus n'a couvert que six couples, et
    # repartir vingt plus loin sauterait quatorze mots-cles qui n'ont jamais
    # ete essayes. Un quota vide ne doit pas creuser de trou dans la liste.
    try:
        if persist:
            INDEED_ETAT.write_text(str((depart + fait) % len(couples)), encoding="utf-8")
    except Exception:
        pass

    etat = "indisponible" if bloque_raison else "quota atteint" if bride else "terminé"
    _log.info(
        f"  Indeed [{etat}] : {len(offers)} offres, {fait} couples, "
        f"{INDEED_REQUETES - debut_http} tentatives HTTP"
    )
    if bride:
        _log.info(
            f"    reprise au couple n° {(depart + fait) % len(couples) + 1} "
            f"sur {len(couples)} a la prochaine passe"
        )
    return offers
