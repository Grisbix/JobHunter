#!/usr/bin/env python3
"""generate_docs.py — Génère CV + lettre pour les offres de la QUEUE qui n'en ont pas
(ou dont les liens sont morts). Remplace l'ancien tailor CLI (qui lisait l'Excel archivé).

Run : python JobHunter.pyw documents --top 30        # top fit sans docs
      python JobHunter.pyw documents --all           # toutes les offres sans docs
      python JobHunter.pyw documents --dry"""

import argparse
import importlib
import sys

from jobhunter import racine as _racine

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper

HERE = _racine.scripts()
QUEUE = HERE / "apply_queue.json"


from jobhunter.programmes.jutil import chemin_de as _p  # helpers partages (voir jutil.py)
from jobhunter.programmes.jutil import url_de as _u


def main():
    # Verrou inter-processus : ce programme reecrit la queue ENTIERE. Si un
    # autre le fait en meme temps (tache planifiee vs app), le dernier qui
    # ecrit efface le travail de l'autre.
    if not importlib.import_module("jobhunter.programmes.jutil").garder(QUEUE):
        return 3
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=30, help="N offres max (tri fit desc)")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument(
        "--sans-source",
        action="store_true",
        help="regenere les lettres dont le PDF n'a plus de .docx : "
        "refresh_letters.py ne peut pas les corriger sur place",
    )
    ap.add_argument(
        "--objet",
        action="store_true",
        help="refait les lettres dont l'objet ne correspond plus a "
        "l'intitule de l'offre (ancienne troncature, ou fichier ecrase)",
    )
    ap.add_argument(
        "--collisions",
        action="store_true",
        help="refait les documents dont le nom a ete ecrase par une "
        "autre offre (contenu parlant d'un autre poste)",
    )
    ap.add_argument(
        "--url",
        default="",
        help="refait CV et lettre de l'offre dont l'URL contient ce texte "
        "(apres une retouche dans CV/Sur_mesure ou Lettres/Sur_mesure)",
    )
    ap.add_argument(
        "--cv-generique",
        action="store_true",
        help="remplace les CV pointant sur un gabarit partage (CV/Modeles) "
        "par un CV adapte a l'offre",
    )
    a = ap.parse_args()

    from jobhunter.stockage import file as queue_io

    # QUEUE explicite : les tests remplacent cette constante par un fichier
    # jetable. Sans elle, charger() lirait la vraie file.
    q = queue_io.charger(QUEUE)  # descriptions reinjectees depuis descriptions.json

    from jobhunter.programmes.rename_docs import new_name

    def _noms_uniques(toutes, kind):
        """stem par offre, sans collision.

        new_name() tronque le poste a 48 caracteres et l'entreprise a 2 mots :
        « Auditeur junior analyste - Nice », « … - Montpellier » et
        « … - Strasbourg » chez Deloitte donnent le MEME nom. Le dernier ecrit
        ecrase les autres, et deux offres se retrouvent liees a une lettre qui
        parle d'une autre ville. On garde le nom nu pour la premiere offre (par
        URL, donc stable d'une execution a l'autre) et on numerote les suivantes.
        """
        # Regroupement en MINUSCULES : Windows ne distingue pas la casse, donc
        # « Auditeur junior analyste » et « Auditeur Junior Analyste » sont deux
        # cles differentes ici mais UN SEUL fichier sur le disque. Grouper en
        # respectant la casse laissait ces paires s'ecraser malgre la numerotation.
        par_nom = {}
        for x in toutes:
            base = new_name(kind, x.get("poste", ""), x.get("entreprise", ""))
            par_nom.setdefault(base.lower(), []).append((base, x))
        out = {}
        for _cle, lot in par_nom.items():
            lot.sort(key=lambda t: str(t[1].get("url") or ""))
            for rang, (base, y) in enumerate(lot):
                out[id(y)] = base if rang == 0 else f"{base}_{rang + 1}"
        return out

    # calcule sur la queue ENTIERE : une offre non regeneree occupe deja son nom
    noms_cv = _noms_uniques(q, "CV")
    noms_lt = _noms_uniques(q, "Lettre")

    def _collision(x):
        """Le document lie ne porte pas le nom unique de CETTE offre.

        Signe qu'une autre offre a ecrase le fichier : le contenu parle d'un
        autre poste ou d'une autre ville.
        """
        for cle, noms in (("cv", noms_cv), ("lettre", noms_lt)):
            p = _p(x.get(cle))
            if p is not None and p.stem.lower() != (noms.get(id(x)) or "").lower():
                return True
        return False

    _RX_XML_T = __import__("re").compile(r"<w:t[^>]*>([^<]*)</w:t>")
    _RX_OBJET = __import__("re").compile(
        r"Objet\s*:\s*Candidature au poste (?:de |d')(.{0,200}?)(?:Madame|Monsieur|$)",
        __import__("re").S,
    )

    def _objet_perime(x):
        """L'objet ECRIT dans la lettre ne correspond pas a l'intitule de l'offre.

        Deux causes, que ce test attrape toutes les deux :
          - la lettre a ete generee avant les regles de nettoyage actuelles et
            porte un mot tronque (« Bordeau » pour « Bordeaux ») ;
          - le fichier a ete ecrase par une autre offre et parle d'un autre poste.
        refresh_letters.py ne sait pas reparer le premier cas : il nettoie le texte
        existant, il ne peut pas deviner la lettre manquante d'un mot ampute.
        """
        import html as _html
        import re as _re
        import zipfile

        p = _p(x.get("lettre"))
        if p is None:
            return False
        d = p.with_suffix(".docx")
        if not d.exists():
            return False
        try:
            with zipfile.ZipFile(d) as z:
                t = _html.unescape(
                    "".join(
                        _RX_XML_T.findall(z.read("word/document.xml").decode("utf-8", "replace"))
                    )
                )
        except Exception:
            return False
        m = _RX_OBJET.search(t)
        if not m:
            return False
        from jobhunter.documents import titre_poste

        lu = _re.sub(r"\s+", " ", m.group(1)).strip()
        return lu != titre_poste(x.get("poste") or "")

    def _cv_generique(x):
        """CV a refaire : soit un gabarit partage, soit un CV dont le PROFIL porte
        encore l'intitule BRUT de l'annonce (« un poste d'ACTUAIRE (F/H) »).

        L'app affiche ce lien en bas de la fiche : l'utilisateur y voit un CV generique
        la ou il attend celui de l'offre.
        """
        p = _p(x.get("cv"))
        if not (p and p.exists()):
            return False
        if p.parent.name != "Par_offre":
            return True
        # On lit le CONTENU, pas l'intitule de l'offre : comparer titre_poste(brut)
        # a brut restait vrai apres regeneration, donc ce selecteur ne convergeait
        # jamais et reproposait sans fin les memes 1012 offres.
        import html as _html
        import re as _re
        import zipfile

        d = p.with_suffix(".docx")
        if not d.exists():
            return False
        try:
            with zipfile.ZipFile(d) as z:
                t = _html.unescape(
                    "".join(
                        _RX_XML_T.findall(z.read("word/document.xml").decode("utf-8", "replace"))
                    )
                )
        except Exception:
            return False
        # Le point de FIN de phrase est suivi d'un blanc. Sans cette condition, la
        # capture s'arretait au premier point rencontre : « Chargé.e de mission »
        # devenait « Chargé » et « Studentjob.ch » perdait son extension, ce qui
        # faisait diverger la comparaison a chaque passe sur des CV pourtant justes.
        m = _re.search(r"recherche d[’']un poste (?:de |d')(.{0,160}?)\.(?=\s|$)", t, _re.S)
        if not m:
            return False
        from jobhunter.documents import titre_poste

        lu = _re.sub(r"\s+", " ", m.group(1)).strip()
        att = titre_poste(x.get("poste") or "")
        # Tolerance au PREFIXE : la capture s'arrete au premier point suivi d'un
        # blanc, donc un titre qui en contient un (« Dipl. Verwaltungssach… »,
        # « …, Paris. 6 months ») est lu tronque alors que le CV est juste. Un CV
        # ecrase par une AUTRE offre ne serait pas un prefixe du titre attendu :
        # on perd la detection d'une troncature reelle, pas celle d'un melange.
        return not (lu == att or (lu and att.startswith(lu)))

    def _sans_source(x):
        """Lettre en PDF dont le .docx source a disparu : incorrigible sur place.

        refresh_letters.py part du .docx et reconvertit ; sans source il ne peut
        rien, et le PDF garde son ancien objet. Seule une regeneration complete
        depuis la queue le remet d'aplomb.
        """
        p = _p(x.get("lettre"))
        return bool(
            p and p.suffix.lower() == ".pdf" and p.exists() and not p.with_suffix(".docx").exists()
        )

    # cibles : cv OU lettre absent / lien mort
    def needs(x):
        for k in ("cv", "lettre"):
            p = _p(x.get(k))
            if p is None or not p.exists():
                return True
        return False

    # Contrats exclus (alternance, stage) : masques dans l'app, donc jamais
    # ouverts. Leur fabriquer un CV et une lettre serait du travail perdu.
    from jobhunter.sources import contrat_du_titre, contrats_exclus

    _EX = contrats_exclus()

    def _visible(x):
        c = (x.get("contrat") or "").strip()
        if c in _EX:
            return False
        return contrat_du_titre(x.get("poste") or "") not in _EX

    if a.sans_source:
        selecteur = _sans_source
    elif a.url:
        selecteur = lambda x: a.url in str(x.get("url") or "")
    elif a.cv_generique:
        selecteur = _cv_generique
    elif a.collisions:
        selecteur = _collision
    elif a.objet:
        selecteur = _objet_perime
    else:
        selecteur = needs
    todo = [x for x in q if _visible(x) and selecteur(x)]
    # fit_fin (2026-10-09) departage les ex aequo d'un meme fit entier.
    todo.sort(key=lambda x: (-(int(x.get("fit") or 0)), -(x.get("fit_fin") or 0)))
    if not a.all:
        todo = todo[: a.top]
    print(f"{len(todo)} offre(s) sans CV/lettre valides{' (top fit)' if not a.all else ''}")
    if a.dry:
        for x in todo[:15]:
            print(f"  fit={x.get('fit')} {x['entreprise'][:24]} — {x['poste'][:45]}")
        return

    from jobhunter.documents import cv_une_page, tailor_letter, to_pdf
    from jobhunter.scoring.langue import langue_offre

    done = 0
    n_en = 0
    for i, x in enumerate(todo):
        # La langue se lit sur l'ANNONCE, pas sur le pays : une offre parisienne
        # d'un gerant international est souvent redigee en anglais, et une offre
        # luxembourgeoise peut etre en francais. 1525 offres de la file sont en
        # anglais, dont 388 en Ile-de-France.
        lg = langue_offre(x.get("poste"), x.get("description"), x.get("localisation"))
        n_en += lg == "en"
        # MISSIONS : le champ dédié SEULEMENT, jamais la description brute.
        # La lettre cite ce texte entre parenthèses — « Les missions que vous
        # décrivez (…) font écho à ces expériences ». Or les 400 premiers
        # caractères d'une annonce sont presque toujours la présentation de
        # l'entreprise : la lettre pour EY Genève citait « At EY, we're all in
        # to shape your future with confidence… », c'est-à-dire le slogan
        # d'EY renvoyé à EY, et coupé en plein mot (« a better wor »).
        # Sans vraies missions, la phrase est simplement omise.
        offer = dict(
            company=x["entreprise"],
            role=x["poste"],
            offer_text=f"{x['poste']} {x.get('description', '')}",
            missions=(x.get("missions") or "")[:400],
            profil=(x.get("profil") or "")[:300],
            domaine=x.get("domaine", ""),
            # Le destinataire, quand l'annonce le nomme. tailor_letter
            # ouvre alors sur « Monsieur X, » au lieu de la generique.
            rh=x.get("rh"),
        )
        try:
            # en mode --cv-generique le CV existe mais c'est un gabarit : on le REMPLACE
            if (
                a.url
                or a.cv_generique
                or a.collisions
                or _p(x.get("cv")) is None
                or not _p(x["cv"]).exists()
            ):
                cv, pdf = cv_une_page(offer, nom=noms_cv.get(id(x)), langue=lg)
                if cv:
                    x["cv"] = _u(pdf or cv)
            # en mode --sans-source le PDF existe : on le REMPLACE (objet perime)
            if (
                a.url
                or a.sans_source
                or a.collisions
                or a.objet
                or _p(x.get("lettre")) is None
                or not _p(x["lettre"]).exists()
            ):
                lt = tailor_letter(offer, nom=noms_lt.get(id(x)), langue=lg)
                if lt:
                    pdf = to_pdf(lt)
                    x["lettre"] = _u(pdf or lt)
            done += 1
            print(f"  ✅ [{i + 1}/{len(todo)}] {x['entreprise'][:28]} — {x['poste'][:40]}")
        except Exception as e:
            print(f"  ! {x['entreprise'][:28]}: {type(e).__name__}")
        if (i + 1) % 10 == 0:
            importlib.import_module("jobhunter.programmes.jutil").jwrite(QUEUE, q)  # checkpoint
    importlib.import_module("jobhunter.programmes.jutil").jwrite(QUEUE, q)
    print(f"\n{done}/{len(todo)} offres équipées (CV+lettre générés, liens à jour).")
    if n_en:
        print(f"   dont {n_en} en ANGLAIS (annonce rédigée en anglais).")


if __name__ == "__main__":
    sys.exit(main())
