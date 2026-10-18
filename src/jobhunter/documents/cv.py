"""CV par offre : copie de la variante, titre, competences ciblees, retouches sur mesure.

Partie de jobhunter.documents (ancien Scripts/tailor_application.py, phase 3.5)."""

import importlib
import json
import shutil
import sys
from typing import Any

from docx import Document

from jobhunter import chemins
from jobhunter import journal as _journal
from jobhunter import paresseux as _paresseux
from jobhunter.documents.commun import CV_ATS, _de, _slug, titre_poste
from jobhunter.documents.rendu import to_pdf
from jobhunter.scoring.lexique import cv_variant_key

_log = _journal.journal(__name__)


_ici = sys.modules[__name__]
# Valeurs tirees du profil : calculees a la premiere lecture, pas a l'import
# (jobhunter.paresseux). Dans ce module, on les lit par `_ici.NOM`.
_PARESSEUX: _paresseux.Fabriques = {}


def __getattr__(nom: str) -> Any:
    return _paresseux.lire(_ici, _PARESSEUX, nom)


_PARESSEUX["CV_OUT"] = lambda: importlib.import_module("jobhunter.documents.commun").CV_OUT


_PARESSEUX["CV_VARIANT"] = lambda: importlib.import_module("jobhunter.scoring.lexique").CV_VARIANT


_PARESSEUX["CV_VARIANT_EN"] = lambda: (
    importlib.import_module("jobhunter.scoring.lexique").CV_VARIANT_EN
)


def cv_sur_mesure(offer):
    """Les retouches de CV ecrites a la main pour cette offre, ou None.

    `CV/Sur_mesure/<entreprise>__<poste>.json`, meme nom tolerant que la lettre :
        {"remplace":    [["texte du modele", "texte pour cette offre"], ...],
         "ajoute_apres": [["texte d'un paragraphe du modele", "nouveau paragraphe"], ...],
         "supprime":    ["texte d'un paragraphe a retirer", ...]}

    `supprime` existe pour la page : ajouter une ligne propre a l'offre fait
    souvent passer le CV a deux pages, et la place se reprend sur ce que cette
    offre-la ne lit pas.

    Le modele reste la source : on ne retouche que ce que l'offre demande, et la
    regeneration reprend les retouches au lieu de les ecraser."""
    from jobhunter.chemins import CV_SUR_MESURE

    if not CV_SUR_MESURE.exists():
        return None
    vise = _slug(f"{offer.get('company')}__{offer.get('role')}")
    for f in CV_SUR_MESURE.glob("*.json"):
        if _slug(f.stem) == vise:
            return json.loads(f.read_text(encoding="utf-8"))
    return None


def appliquer_cv_sur_mesure(doc, retouches):
    """Applique les retouches a un Document. Rend la liste des ancres introuvables.

    Le remplacement se fait DANS le run qui porte le texte : la ligne d'une
    experience melange un intitule gras et une date tabulee, et reecrire le
    paragraphe entier perdrait cette mise en forme. Une ancre introuvable est
    SIGNALEE, jamais ignoree : le modele a pu changer, et une retouche qui ne
    s'applique plus enverrait le CV generique sans un mot."""
    import copy

    manquees = []
    for ancien, nouveau in retouches.get("remplace", []):
        fait = False
        for p in doc.paragraphs:
            for r in p.runs:
                if ancien in r.text:
                    r.text = r.text.replace(ancien, nouveau)
                    fait = True
            if not fait and ancien in p.text:
                txt = p.text.replace(ancien, nouveau)
                for r in p.runs:
                    r.text = ""
                p.runs[0].text = txt
                fait = True
        if not fait:
            manquees.append(ancien)
    for ancre, texte in retouches.get("ajoute_apres", []):
        p = next((p for p in doc.paragraphs if ancre in p.text), None)
        if p is None:
            manquees.append(ancre)
            continue
        el = copy.deepcopy(p._p)
        p._p.addnext(el)
        from docx.text.paragraph import Paragraph

        neuf = Paragraph(el, p._parent)
        for r in neuf.runs:
            r.text = ""
        neuf.runs[0].text = texte
    for ancre in retouches.get("supprime", []):
        p = next((p for p in doc.paragraphs if ancre in p.text), None)
        if p is None:
            manquees.append(ancre)
            continue
        p._p.getparent().remove(p._p)
    return manquees


# ---- CV : injecte titre + ligne competences ciblees ----
def tailor_cv(offer, nom=None, langue="fr", allege=0, auto=True):
    """`nom` : stem impose. Sans lui, plusieurs offres au titre voisin
    produisent le MEME fichier et s'ecrasent — voir generate_docs._noms_uniques.

    `langue` : 'en' choisit le modele anglais quand il existe. 1525 offres de la
    file sont redigees en anglais ; leur envoyer un CV francais, c'est se
    disqualifier avant lecture. Le repli sur le francais est SILENCIEUX quand le
    modele anglais manque (toutes les variantes ne sont pas encore traduites) —
    un CV francais vaut mieux que pas de CV."""
    chemins.preparer()  # dossiers de sortie, au moment d'ecrire
    key = cv_variant_key(offer["domaine"])
    src = CV_ATS / (_ici.CV_VARIANT.get(key) or "")
    if not _ici.CV_VARIANT.get(key):
        # Variante sans fichier : le premier CV du profil qui existe.
        src = next(
            (CV_ATS / f for f in _ici.CV_VARIANT.values() if f and (CV_ATS / f).exists()), src
        )
    if (
        langue == "en"
        and _ici.CV_VARIANT_EN.get(key)
        and (CV_ATS / _ici.CV_VARIANT_EN[key]).exists()
    ):
        src = CV_ATS / _ici.CV_VARIANT_EN[key]
    if not src.is_file():
        _log.info(f"  ! CV variante absente: {src.name or key} (profil.json, domaines[].cv)")
        return None
    from rename_docs import new_name

    if src.suffix.lower() == ".pdf":
        # CV fourni en PDF seulement : il part tel quel, sans adaptation.
        # Un modele .docx permet d'y inserer l'intitule du poste.
        out = _ici.CV_OUT / (
            (nom or new_name("CV", offer.get("role") or "", offer["company"])) + ".pdf"
        )
        shutil.copyfile(src, out)
        return out
    doc = Document(str(src))
    # Le marqueur est dans le PROFIL : « je suis a la recherche d'un poste de
    # [nom du poste] ». Y coller l'intitule BRUT donnait « d'ACTUAIRE (F/H) » ou
    # « d'Adjoint Risque Clients (F/H) - CDD » : la mention de genre et le type de
    # contrat n'ont rien a faire dans une phrase ecrite a la premiere personne.
    # Sur un CV le titre entre DANS une phrase : il doit se lire, pas seulement
    # etre exact. « …a la recherche d'un poste d'Analyste RSE-ESG - Analyste
    # Credit et ESG. » ou « …a position as Consultant, Climate Change and
    # Sustainability Services Financial Services. » trainent le titre d'annonce
    # entier, tiret de separation compris. On garde le premier segment quand il
    # suffit a nommer le metier ; l'objet de la LETTRE, lui, conserve le titre
    # complet, parce qu'il doit correspondre exactement a l'annonce.
    role = titre_poste(offer.get("role") or "") or "ce poste"
    # UN TITRE TROP LONG FAIT DEBORDER LE CV SUR DEUX PAGES. Il s'insere DANS
    # une phrase du profil, qui tient sur trois lignes et n'a qu'un point de
    # marge. Mesure du 2026-09-22 sur les intitules ESG de la file : deux des
    # trois plus longs passaient le CV a deux pages, en silence.
    #
    # On ne coupe donc pas seulement sur « - » : les annonces empilent aussi
    # des virgules, des parentheses et des barres obliques. « Investment
    # Banking, Natural Resources & Energy Transition (Power/Energy) » devient
    # « Investment Banking », qui se lit et tient.
    #
    # Le seuil de 12 caracteres protege les tetes trop courtes pour nommer un
    # metier : « Stage » ou « VIE » seuls ne disent rien.
    for sep in (" - ", " – ", ", ", " (", " / ", " | "):
        tete = role.split(sep)[0].strip()
        if 12 <= len(tete) < len(role):
            role = tete
    # Dernier filet, si aucun separateur n'apparait : on coupe sur un mot.
    if len(role) > 46:
        coupe = role[:46]
        i = coupe.rfind(" ")
        role = (coupe[:i] if i > 28 else coupe).rstrip(" ,;:.-&")

    # 1) remplace le titre [nom du poste], avec l'elision de _de() (h et y exclus)
    #    Le modele anglais porte « [job title] » et ne demande AUCUNE elision :
    #    « as [job title] » se construit sans article contracte.
    for p in doc.paragraphs:
        if "[job title]" in p.text:
            txt = p.text.replace("[job title]", role)
        elif "[nom du poste]" in p.text:
            if "de [nom du poste]" in p.text:
                # Apostrophe TYPOGRAPHIQUE : le gabarit ecrit « d’un poste ».
                txt = p.text.replace("de [nom du poste]", _de(role, "’"))
            else:
                txt = p.text.replace("[nom du poste]", role)
        else:
            continue
        for r in p.runs:
            r.text = ""
        (p.runs[0] if p.runs else p.add_run("")).text = txt

    # 1 bis) Retouches ecrites a la main pour CETTE offre (CV/Sur_mesure).
    #       Sans elles, les faits automatiques de CV/Faits.json (cv_auto) :
    #       le sur-mesure, relu par l'utilisateur, l'emporte toujours.
    retouches = cv_sur_mesure(offer)
    if retouches:
        manquees = appliquer_cv_sur_mesure(doc, retouches)
        for m in manquees:
            _log.info(f"  ! CV sur mesure : texte introuvable dans le modele : « {m[:60]} »")
    elif auto:
        from jobhunter.documents import cv_auto

        r = cv_auto.retouches(
            offer.get("offer_text") or offer.get("role") or "",
            langue if langue == "en" else "fr",
            allege,
        )
        # Ancres manquees : NORMAL ici. Chaque variante de CV n'a pas les memes
        # lignes, et un fait vise parfois une seule d'entre elles.
        appliquer_cv_sur_mesure(doc, r)

    # 2) SUPPRIMÉ (2026-07-12) : la ligne « Compétences ciblées pour ce poste : … »
    #    trahissait un CV auto-généré auprès des recruteurs. Les skills servent toujours
    #    au scoring (fit/ATS) et à la LETTRE, mais ne sont plus injectés dans le CV.

    from rename_docs import new_name  # Prenom_Nom_CV_<Poste court>_<Entreprise>

    out = _ici.CV_OUT / ((nom or new_name("CV", role, offer["company"])) + ".docx")
    doc.save(str(out))
    return out


def _pages_pdf(pdf):
    try:
        import fitz

        with fitz.open(str(pdf)) as d:
            return d.page_count
    except Exception:
        return 1  # illisible : on ne boucle pas pour rien


def cv_une_page(offer, nom=None, langue="fr"):
    """tailor_cv + to_pdf, en garantissant UNE page. Rend (docx, pdf).

    Les faits automatiques ajoutent des lignes ; si le PDF deborde, on retire
    les `allegements` de CV/Faits.json un par un. En dernier recours, le CV
    repart du modele sans fait automatique : un CV generique d'une page vaut
    mieux qu'un CV adapte de deux. Un CV/Sur_mesure n'est jamais allege : il a
    ete relu, sa page aussi."""
    chemins.preparer()  # dossiers de sortie, au moment d'ecrire
    from jobhunter.documents import cv_auto

    lg = langue if langue == "en" else "fr"
    essais = [(k, True) for k in range(cv_auto.nb_allegements(lg) + 1)] + [(0, False)]
    if cv_sur_mesure(offer):
        essais = [(0, True)]
    cv = pdf = None
    for allege, auto in essais:
        cv = tailor_cv(offer, nom=nom, langue=langue, allege=allege, auto=auto)
        if not cv:
            return None, None
        pdf = to_pdf(cv)
        if not pdf or _pages_pdf(pdf) <= 1:
            break
    return cv, pdf
