#!/usr/bin/env python3
"""generate_docs.py — Generates CV + letter for the QUEUE's offers that have none
(or whose links are dead). Replaces the old tailor CLI (which read the archived Excel).

Run: python JobHunter.pyw documents --top 30        # top fit without docs
     python JobHunter.pyw documents --all           # all the offers without docs
     python JobHunter.pyw documents --dry"""

import argparse
import importlib
import sys

from jobhunter import root as _racine

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper

HERE = _racine.scripts()
QUEUE = HERE / "apply_queue.json"


from jobhunter.programs.util import chemin_de as _p  # helpers partages (voir util.py)
from jobhunter.programs.util import url_de as _u


def main():
    # Inter-process lock: this program rewrites the ENTIRE queue. If
    # another one does it at the same time (scheduled task vs app), the last one
    # to write erases the other's work.
    if not importlib.import_module("jobhunter.programs.util").garder(QUEUE):
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

    from jobhunter.storage import queue as queue_io

    # Explicit QUEUE: the tests replace this constant with a throwaway
    # file. Without it, charger() would read the real queue.
    q = queue_io.charger(QUEUE)  # descriptions reinjectees depuis descriptions.json

    from jobhunter.programs.rename_docs import new_name

    def _noms_uniques(toutes, kind):
        """stem per offer, without collision.

        new_name() truncates the job to 48 characters and the company to 2 words:
        "Auditeur junior analyste - Nice", "… - Montpellier" and
        "… - Strasbourg" at Deloitte give the SAME name. The last one written
        overwrites the others, and two offers end up linked to a letter that talks
        about another city. We keep the bare name for the first offer (by URL, hence
        stable from one run to the next) and number the following ones.
        """
        # Grouping in LOWER CASE: Windows does not distinguish case, so
        # "Auditeur junior analyste" and "Auditeur Junior Analyste" are two
        # different keys here but ONE SINGLE file on disk. Grouping
        # case-sensitively let these pairs overwrite each other despite the numbering.
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

    # computed on the ENTIRE queue: an offer not regenerated already holds its name
    noms_cv = _noms_uniques(q, "CV")
    noms_lt = _noms_uniques(q, "Lettre")

    def _collision(x):
        """The linked document does not carry THIS offer's unique name.

        A sign that another offer overwrote the file: the content talks about another
        job or another city.
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
        """The subject WRITTEN in the letter does not match the offer's title.

        Two causes, which this test catches both:
          - the letter was generated before the current cleaning rules and
            carries a truncated word ("Bordeau" for "Bordeaux");
          - the file was overwritten by another offer and talks about another job.
        refresh_letters.py cannot repair the first case: it cleans the existing
        text, it cannot guess the missing letter of a truncated word.
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
        """CV to redo: either a shared template, or a CV whose PROFILE still carries the
        RAW title of the posting ("un poste d'ACTUAIRE (F/H)").

        The app displays this link at the bottom of the card: the user sees a generic
        CV there where they expect the offer's.
        """
        p = _p(x.get("cv"))
        if not (p and p.exists()):
            return False
        if p.parent.name not in ("Par_offre", "By_offer"):
            return True
        # We read the CONTENT, not the offer's title: comparing titre_poste(raw)
        # with raw stayed true after regeneration, so this selector never
        # converged and endlessly proposed the same 1012 offers again.
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
        # The END-of-sentence full stop is followed by a blank. Without this condition, the
        # capture stopped at the first full stop met: "Chargé.e de mission"
        # became "Chargé" and "Studentjob.ch" lost its extension, which
        # made the comparison diverge at each pass on CVs that were in fact right.
        m = _re.search(r"recherche d[’']un poste (?:de |d')(.{0,160}?)\.(?=\s|$)", t, _re.S)
        if not m:
            return False
        from jobhunter.documents import titre_poste

        lu = _re.sub(r"\s+", " ", m.group(1)).strip()
        att = titre_poste(x.get("poste") or "")
        # PREFIX tolerance: the capture stops at the first full stop followed by a
        # blank, so a title that contains one ("Dipl. Verwaltungssach…",
        # "…, Paris. 6 months") is read truncated while the CV is right. A CV
        # overwritten by ANOTHER offer would not be a prefix of the expected title:
        # we lose the detection of a real truncation, not that of a mix-up.
        return not (lu == att or (lu and att.startswith(lu)))

    def _sans_source(x):
        """PDF letter whose source .docx has disappeared: cannot be fixed in place.

        refresh_letters.py starts from the .docx and converts again; without a source
        it can do nothing, and the PDF keeps its old subject. Only a full regeneration
        from the queue puts it right.
        """
        p = _p(x.get("lettre"))
        return bool(
            p and p.suffix.lower() == ".pdf" and p.exists() and not p.with_suffix(".docx").exists()
        )

    # targets: cv OR letter missing / dead link
    def needs(x):
        for k in ("cv", "lettre"):
            p = _p(x.get(k))
            if p is None or not p.exists():
                return True
        return False

    # Excluded contracts (work-study, internship): hidden in the app, hence never
    # opened. Making them a CV and a letter would be wasted work.
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
    # fit_fin (2026-10-09) breaks ties between offers with the same integer fit.
    todo.sort(key=lambda x: (-(int(x.get("fit") or 0)), -(x.get("fit_fin") or 0)))
    if not a.all:
        todo = todo[: a.top]
    print(f"{len(todo)} offre(s) sans CV/lettre valides{' (top fit)' if not a.all else ''}")
    if a.dry:
        for x in todo[:15]:
            print(f"  fit={x.get('fit')} {x['entreprise'][:24]} — {x['poste'][:45]}")
        return

    from jobhunter.documents import cv_une_page, tailor_letter, to_pdf
    from jobhunter.scoring.language import langue_offre

    done = 0
    n_en = 0
    for i, x in enumerate(todo):
        # The language is read on the POSTING, not on the country: a Paris offer
        # from an international asset manager is often written in English, and a
        # Luxembourg offer may be in French. 1525 offers of the queue are in
        # English, 388 of them in Île-de-France.
        lg = langue_offre(x.get("poste"), x.get("description"), x.get("localisation"))
        n_en += lg == "en"
        # MISSIONS: the dedicated field ONLY, never the raw description.
        # The letter quotes this text between parentheses — "Les missions que vous
        # décrivez (…) font écho à ces expériences". But the first 400
        # characters of a posting are almost always the presentation of
        # the company: the letter for EY Geneva quoted "At EY, we're all in
        # to shape your future with confidence…", i.e. EY's slogan
        # sent back to EY, and cut in the middle of a word ("a better wor").
        # Without real missions, the sentence is simply left out.
        offer = dict(
            company=x["entreprise"],
            role=x["poste"],
            offer_text=f"{x['poste']} {x.get('description', '')}",
            missions=(x.get("missions") or "")[:400],
            profil=(x.get("profil") or "")[:300],
            domaine=x.get("domaine", ""),
            # The recipient, when the posting names them. tailor_letter
            # then opens with "Monsieur X," instead of the generic one.
            rh=x.get("rh"),
        )
        try:
            # in --cv-generique mode the CV exists but it is a template: we REPLACE it
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
            # in --sans-source mode the PDF exists: we REPLACE it (stale subject)
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
            importlib.import_module("jobhunter.programs.util").jwrite(QUEUE, q)  # checkpoint
    importlib.import_module("jobhunter.programs.util").jwrite(QUEUE, q)
    print(f"\n{done}/{len(todo)} offres équipées (CV+lettre générés, liens à jour).")
    if n_en:
        print(f"   dont {n_en} en ANGLAIS (annonce rédigée en anglais).")


if __name__ == "__main__":
    sys.exit(main())
