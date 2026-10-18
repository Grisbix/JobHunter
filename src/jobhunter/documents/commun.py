"""Ce que partagent CV, lettre et message : intitule nettoye, competences, valeurs d'entreprise.

Partie de jobhunter.documents (ancien Scripts/tailor_application.py, phase 3.5)."""

# Noms du lexique, re-exportes : `tailor_application.cv_variant_key` reste valable.
import re

from jobhunter import chemins
from jobhunter import profil as _P
from jobhunter.scoring.lexique import (  # noqa: F401
    _COMP,
    _DOMAINES,
    CV_VARIANT,
    CV_VARIANT_EN,
    SKILL_LEX,
    cv_variant_key,
    has_skill,
)

CV_ATS = chemins.CV_MODELES


# Dossiers de sortie : crees au moment d'ecrire (chemins.preparer), pas a l'import.
CV_OUT, LT_OUT = chemins.CV_PAR_OFFRE, chemins.LT_PAR_OFFRE


_ID = _P.identite()


PROFILE = dict(nom=_ID["nom"], ville=_ID["ville"], email=_ID["email"], tel=_ID["tel"])


# accroche valeur par entreprise : profil, lettre.valeurs_entreprises_fr/en
COMPANY_VALUE = dict(_P.get("lettre.valeurs_entreprises_fr", {}) or {})


# Mots qui gardent leur majuscule dans un intitule de poste : noms propres
# residuels. La regle generale est qu'un intitule francais est un NOM COMMUN
# (« contrôleur de gestion », pas « Contrôleur de Gestion »), mais les annonces
# capitalisent chaque mot a l'anglaise et on recopiait tel quel.
_PROPRES = {
    "france",
    "paris",
    "europe",
    "afrique",
    "asie",
    "amerique",
    "amérique",
    "allemagne",
    "espagne",
    "italie",
    "belgique",
    "suisse",
    "luxembourg",
    "benelux",
    "emea",
    "monde",
}


# Les sigles qui gardent leurs capitales meme dans un intitule hurle. Liste
# EXPLICITE : aucune regle de longueur ne separe « ESG » de « DES ».
_SIGLES = {
    "ESG",
    "RSE",
    "ISR",
    "SFDR",
    "CSRD",
    "CSDDD",
    "GRI",
    "TCFD",
    "SASB",
    "PAI",
    "DCF",
    "LBO",
    "M&A",
    "IFRS",
    "EBITDA",
    "KPI",
    "ERP",
    "SAP",
    "IT",
    "SI",
    "DSI",
    "BI",
    "SQL",
    "VBA",
    "IA",
    "AI",
    "ML",
    "LLM",
    "RH",
    "QHSE",
    "HSE",
    "RGPD",
    "AMF",
    "ACPR",
    "BFR",
    "FP&A",
    "PME",
    "ETI",
    "ONG",
    "SRI",
    "UX",
    "UI",
    "API",
    "CRM",
    "PMO",
    "MOA",
    "MOE",
}


def minuscule_titre(t):
    """« Contrôleur de Gestion Financier » -> « contrôleur de gestion financier ».

    Un sigle reste intact (« Analyste RSE-ESG » garde RSE-ESG), un nom propre
    connu aussi. Tout le reste passe en bas de casse : en francais un intitule
    de poste est un nom commun.

    MAIS une annonce peut etre ecrite ENTIEREMENT en capitales — « CORPORATE
    FINANCE », « GESTIONNAIRE DES RISQUES ». Prendre chaque mot pour un sigle
    laissait alors l'objet de la lettre hurler. Quand la majorite des mots
    longs sont en capitales, c'est une annonce qui crie, pas une suite de
    sigles : on abaisse TOUT, et on ne releve que les sigles reconnus.

    La longueur ne suffit pas a distinguer un sigle : « DES » fait trois
    lettres et reste un article, d'ou « gestionnaire DES risques ».
    """
    mots = (t or "").split(" ")
    longs = [m.strip(",.;:()[]") for m in mots if len(m.strip(",.;:()[]")) > 4]
    crie = bool(longs) and sum(1 for m in longs if m.upper() == m) > len(longs) / 2

    sortie = []
    for m in mots:
        nu = m.strip(",.;:()[]")
        if not nu:
            sortie.append(m)
        elif nu.lower() in _PROPRES:
            # Un nom propre garde sa majuscule, mais pas TOUTES ses capitales :
            # « CHARGE DE MISSION RSE FRANCE » donnait « … RSE FRANCE ».
            sortie.append(m.capitalize() if crie else m)
        elif crie:
            sortie.append(m if nu.upper() in _SIGLES else m.lower())
        elif nu.upper() == nu and any(c.isalpha() for c in nu):
            sortie.append(m)  # sigle : RSE, M&A, IT, SAP
        else:
            sortie.append(m.lower())
    return " ".join(sortie)


def _de(mot, apostrophe="'"):
    """Élision : 'de Amundi' -> \"d'Amundi\".

    'h' et 'y' EXCLUS : « de Hollande » et « de Yann » sont corrects, pas « d'Hollande ».

    `apostrophe` : le gabarit de CV est écrit avec l'apostrophe TYPOGRAPHIQUE
    (« d’une expertise », « d’un mémoire »). Y injecter une apostrophe droite
    donnait, dans la même phrase : « d’un poste d'Analyste RSE-ESG ». Deux
    apostrophes différentes à six mots d'intervalle, sur un CV.
    """
    mot = (mot or "").strip()
    if mot[:1].lower() in "aàâäeéèêëiîïoôöuùûü":
        return "d" + apostrophe + mot
    return "de " + mot


# ── Nettoyage de l'intitulé de poste ────────────────────────────────────────
# Le titre brut d'une annonce n'est PAS un intitulé de poste : il porte la mention
# de genre, le type de contrat, la ville, la référence interne… Écrit tel quel dans
# « Objet : Candidature au poste de … », il donne des lettres illisibles.
# Les \b sont INDISPENSABLES : sans eux, « DAF - Finance » matche « F - F »
# (le F final de DAF, le tiret, le F initial de Finance) et le nettoyage produit
# « DA inance ». Le motif ne doit accepter que des lettres ISOLEES.
RX_GENRE = re.compile(r"[(\[]?\s*\b[HFMWX]\b(?:\s*[/|.-]\s*\b[HFMWXD]\b){1,2}\s*[)\]]?", re.I)


# Le marqueur de genre COLLE, sans separateur : « CORPORATE FINANCE HF ».
# RX_GENRE exige un separateur (H/F, H-F, H.F) et laissait donc passer celui-ci,
# si bien que l'objet annoncait un poste de « corporate finance hf ». Ancre en
# FIN de chaine seulement : ailleurs, « HF » peut vouloir dire haute frequence.
RX_GENRE_COLLE = re.compile(r"\s*[(\[]?\s*\b(?:HF|FH|MW|FM|MF)\b\s*[)\]]?\s*$", re.I)


RX_CONTRAT = re.compile(
    r"\b(CDI|CDD|VIE|V\.I\.E|int[ée]rim|freelance|temps\s+plein|temps\s+partiel|"
    r"full[\s-]?time|part[\s-]?time|permanent|remote|t[ée]l[ée]travail|hybride|"
    r"\d+\s*mois|\d+\s*months|\d+\s*ans)\b",
    re.I,
)


RX_BRUIT = re.compile(
    r"\b(nouveau|new|urgent|poste\s+\d+|r[ée]f\.?\s*\S+|"
    r"job\s*id\s*:?\s*\d+|\d{3,}\s*days?)\b",
    re.I,
)


# « #00137324 » : aucun caractère de mot devant le #, donc un \b devant ne matcherait JAMAIS
RX_REF = re.compile(r"#\s*\d+")


RX_LIEU_FIN = re.compile(r"[\s,(-]+[A-ZÀ-Ý][\wÀ-ÿ'-]*\s*\(?\d{5}\)?\s*\)?\s*$")


RX_ADRESSE = re.compile(
    r"\b\d{1,4}\s+(rue|avenue|boulevard|impasse|chemin|place)\b"
    r"|\b\d{5}\s+[A-ZÀ-Ý]",
    re.I,
)


for _n, _rx in list(globals().items()):
    # Un « \b » mangé par un heredoc devient \x08 : le motif ne matche plus jamais,
    # sans erreur. On refuse de démarrer plutôt que de générer des lettres fausses.
    if _n.startswith("RX_") and hasattr(_rx, "pattern"):
        assert "\x08" not in _rx.pattern, "motif corrompu (backspace littéral) : " + _n


def titre_poste(t, maxlen=80):
    """Intitulé lisible à partir du titre brut d'une annonce.

    Coupe au dernier séparateur AVANT maxlen, jamais au milieu d'un mot.
    Renvoie "" si ce n'est pas un intitulé de poste (adresse postale, vide) :
    l'appelant écrit alors une formule neutre plutôt qu'une phrase absurde.
    """
    t = re.sub(r"\s+", " ", (t or "").strip())
    if RX_ADRESSE.search(t):
        return ""
    t = RX_GENRE.sub(" ", t)
    t = RX_GENRE_COLLE.sub("", t)
    t = RX_CONTRAT.sub(" ", t)
    t = RX_BRUIT.sub(" ", t)
    t = RX_REF.sub(" ", t)
    # Parentheses vides ou reduites a des chiffres/ponctuation par les coupes
    # precedentes : « CDD (2.5 mois) » laissait « - (2. ) » une fois le contrat
    # et la duree retires.
    t = re.sub(r"[(\[]\s*[\d.,;:\s-]*\s*[)\]]", " ", t)
    t = re.sub(r"\s*,(\s*,)+", ",", t)
    t = RX_LIEU_FIN.sub("", t)
    # séparateurs : uniquement ceux ENTOURÉS d'espaces — « LCB-FT » et « H2-Power »
    # sont des mots, pas des séparateurs
    t = re.sub(r"\s+[-–—:|]\s+", " - ", t)
    t = re.sub(r"\s*[–—:|]\s*", " - ", t)
    t = re.sub(r"(\s*-\s*){2,}", " - ", t)
    t = re.sub(r"\s{2,}", " ", t).strip(" -,.;:|")
    if len(t) > maxlen:
        coupe = t[:maxlen]
        for sep in (" - ", ", ", " "):
            i = coupe.rfind(sep)
            if i > maxlen * 0.5:
                coupe = coupe[:i]
                break
        t = coupe.strip(" -,.;:|")
    return t


def _coupe_mot(t, n):
    """Tronque a n caracteres SANS couper un mot, et sans laisser de ponctuation
    pendante. « …help to build a better wor » est parti dans une vraie lettre :
    une citation coupee en plein mot est plus visible qu'une citation absente."""
    t = " ".join((t or "").split())
    if len(t) <= n:
        return t.rstrip(" ,;:.-")
    coupe = t[:n]
    i = coupe.rfind(" ")
    if i > n * 0.6:
        coupe = coupe[:i]
    return coupe.rstrip(" ,;:.-") + "…"


def company_value(company):
    """Accroche connue pour cette entreprise, ou "" : quand l'entreprise est
    inconnue, la lettre ne lui prete AUCUN engagement, elle parle du poste."""
    c = (company or "").lower()
    for k, v in COMPANY_VALUE.items():
        if k in c:
            return v
    return ""


# ── LE CORPS ECRIT A LA MAIN ─────────────────────────────────────────────────
# Le gabarit sert 5374 annonces. Il ne peut donc rien dire de precis sur
# aucune : il nomme des competences, jamais un fonds, jamais une mission de
# l'annonce. C'est le bon compromis pour une candidature de masse et le
# mauvais pour les cinq offres de l'annee qui meritent une heure de travail.
#
# Quand `Lettres/Sur_mesure/<entreprise>__<poste>.txt` existe, ses paragraphes
# remplacent le CORPS. Tout le reste continue d'etre genere : l'en-tete, la
# date, l'objet, la formule d'appel — qui sait nommer deux destinataires — et
# la reprise de cloture accordee. On ne reecrit pas a la main ce que le code
# fait mieux.
#
# C'est une ENTREE, au meme titre que CV/Modeles : `regenere_docs.py` ne la
# touche pas, et regenerer la lettre la reprend telle quelle.
_RX_SLUG = re.compile(r"[^a-z0-9]+")


def _slug(s):
    return _RX_SLUG.sub("_", (s or "").lower()).strip("_")


# Libelles de competences en ANGLAIS. La lettre anglaise les cite en toutes
# lettres ; les laisser en francais trahit la generation automatique plus
# surement qu'une faute de style. Les sigles reglementaires (SFDR, CSRD, GRI,
# TCFD, PAI) ne se traduisent PAS : ce sont les memes textes europeens.
SKILL_EN = {lab: v.get("en") or lab for lab, v in _COMP.items()}


_SKILL_EN_NORM = None


def skills_en(labels):
    """Libelles traduits. La recherche ignore les ACCENTS : les cles de SKILL_EN
    sont ecrites sans eux, les libelles reels en portent (« Analyse financiere »
    contre « Analyse financiere »). Comparer tels quels ne trouvait rien et la
    lettre anglaise restait farcie de francais.

    Un libelle inconnu est RENDU TEL QUEL plutot que supprime : mieux vaut un
    mot francais visible qu'une competence disparue."""
    global _SKILL_EN_NORM
    if _SKILL_EN_NORM is None:
        from jutil import sans_accent

        _SKILL_EN_NORM = {sans_accent(k).lower(): v for k, v in SKILL_EN.items()}
    from jutil import sans_accent

    return [_SKILL_EN_NORM.get(sans_accent(x).lower(), x) for x in labels]


# Libelles qui servent au SCORING mais ne s'ecrivent pas dans une lettre : ce
# sont des noms de categorie internes, pas des competences. « Durabilité / ESG
# (généraliste) » s'est retrouve tel quel, parentheses comprises, dans une
# lettre anglaise envoyee a EY Geneve — au milieu de SFDR et GRI/TCFD, il
# signalait le systeme qui l'avait ecrite.
SKILL_INTERNES = {lab for lab, v in _COMP.items() if v.get("interne")}


def match_skills(offer_text, max_n=8):
    t = (offer_text or "").lower()
    hits = []
    for label in SKILL_LEX:
        if label in SKILL_INTERNES:
            continue
        if has_skill(label, t):
            hits.append(label)
    # socle neutre (pas de biais ESG) si offre pauvre en texte
    if len(hits) < 3:
        for base in _P.get("competences_de_base", []) or []:
            if base not in hits:
                hits.append(base)
    return hits[:max_n]
