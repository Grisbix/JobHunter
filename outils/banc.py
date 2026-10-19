#!/usr/bin/env python3
"""banc.py — Non-regression bench: proves that a rewrite changes nothing.

For each offer of a set, it records what the engine DECIDES: title filter, fit,
fit_fin, required experience, domain, sorting reason, zone, country, contract,
language, language cap, and the text of the message. For a sample, it also records
the full text of the letter and of the CV (date neutralised).
Nothing is written to disk outside the output file: saving the .docx files is
intercepted.

    python outils/banc.py enregistrer outils/banc_reference.json
    python outils/banc.py comparer   outils/banc_reference.json

Sets:
  - by default, the FICTITIOUS offers of outils/banc_offres.py on the example
    profile — the CI set, versioned with its reference;
  - --file <apply_queue.json> --profil <profil.json>: a real queue (in
    Recherche_emploi), reference kept out of git.

A difference is not necessarily a bug: if the change is intended, the reference
is regenerated in the SAME commit, and the message says why.

Decision: docs/adr/0006-banc-de-non-regression.md
"""

import argparse
import difflib
import hashlib
import json
import os
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SCRIPTS = RACINE / "Scripts"
EXEMPLE = RACINE / "profil" / "exemple_finance_esg.json"
VERSION_FORMAT = 1

_MOIS = (
    r"janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|"
    r"novembre|décembre|decembre|January|February|March|April|May|June|July|August|"
    r"September|October|November|December"
)
_RX_DATE = re.compile(
    rf"\b\d{{1,2}}(?:er)?\s+(?:{_MOIS})\s+\d{{4}}\b|"
    rf"\b(?:{_MOIS})\s+\d{{1,2}},\s+\d{{4}}\b",
    re.I,
)


def _neutre(texte):
    """Today's date changes every day: it is not a decision of the engine."""
    return _RX_DATE.sub("<DATE>", texte)


def _texte_docx(doc):
    lignes = [p.text for p in doc.paragraphs]
    for t in doc.tables:
        for rangee in t.rows:
            lignes.append(" | ".join(c.text for c in rangee.cells))
    return _neutre("\n".join(lignes))


class Capture:
    """Replaces Document.save: keeps the text, writes nothing."""

    def __init__(self):
        self.textes = []

    def __enter__(self):
        import docx.document

        self._classe = docx.document.Document
        self._save = self._classe.save
        capture = self

        def save(doc, chemin, *a, **k):
            capture.textes.append(_texte_docx(doc))

        self._classe.save = save
        return self

    def __exit__(self, *exc):
        self._classe.save = self._save


def _sur(f, *a, **k):
    """An exception is a result like any other: it must stay the same."""
    try:
        return f(*a, **k)
    except Exception as e:  # noqa: BLE001 — we record the type, on purpose
        return f"ERREUR {type(e).__name__}"


def mesurer(offres, cle, n_docs):
    """{key: decisions} for each offer."""
    sys.path[:0] = [str(SCRIPTS.parent / "src"), str(SCRIPTS)]  # the engine measures
    from jobhunter import documents as tailor_application
    from jobhunter import sources as job_sources
    from jobhunter.documents import message as message_offre
    from jobhunter.programmes.scrape_jobs import classify_domaine
    from jobhunter.scoring import fit as ats_match
    from jobhunter.scoring import langue, zones
    from jobhunter.scoring import tri as tri_file

    resultats = {}
    pas = max(1, len(offres) // n_docs) if n_docs else 0
    for i, o in enumerate(offres):
        titre, desc = o.get("poste") or "", o.get("description") or ""
        lieu = o.get("localisation") or ""
        texte = f"{titre} {desc}"
        fit = _sur(ats_match.fit_detail, texte, titre)
        o = dict(o, domaine=_sur(classify_domaine, titre))
        if isinstance(fit, tuple):
            o.update(fit=fit[0], exp_requise=fit[1], fit_fin=fit[2])
        r = {
            "title_ok": _sur(job_sources.title_ok, titre),
            "fit": list(fit) if isinstance(fit, tuple) else fit,
            "domaine": o["domaine"],
            "tri": _sur(tri_file.motif, o, set()),
            "zone": _sur(zones.zone_lieu, lieu),
            "pays": _sur(zones.pays_lieu, lieu),
            "contrat": _sur(
                job_sources.contrat_de_la_description,
                desc,
                _sur(job_sources.contrat_du_titre, titre),
            ),
            "langue": _sur(langue.langue_offre, titre, desc, lieu),
            "plafond_langue": _sur(ats_match.plafond_langue, texte),
            "message": _neutre(str(_sur(message_offre.message, o))),
        }
        if pas and i % pas == 0:
            offre_doc = dict(
                company=o.get("entreprise") or "",
                role=titre,
                offer_text=texte,
                missions=(o.get("missions") or "")[:400],
                profil=(o.get("profil") or "")[:300],
                domaine=o["domaine"],
                rh=o.get("rh"),
            )
            lg = r["langue"] if r["langue"] in ("fr", "en") else "fr"
            with Capture() as c:
                err_l = _sur(tailor_application.tailor_letter, offre_doc, nom="banc", langue=lg)
            r["lettre"] = c.textes[-1] if c.textes else str(err_l)
            with Capture() as c:
                err_c = _sur(tailor_application.tailor_cv, offre_doc, nom="banc", langue=lg)
            r["cv"] = c.textes[-1] if c.textes else str(err_c)
        resultats[cle(i, o)] = json.loads(json.dumps(r, default=str))
    return resultats


def charger_jeu(a):
    if a.file:
        sys.path[:0] = [str(SCRIPTS.parent / "src"), str(SCRIPTS)]
        from jobhunter.stockage import file as queue_io

        offres = queue_io.charger(Path(a.file))
        return offres, (lambda i, o: queue_io.oid(o))
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import banc_offres

    return banc_offres.offres(), (lambda i, o: f"{i:03d}|{o['poste']}")


def comparer(ref, nouveau, max_aff=25):
    ecarts = []
    for k in sorted(set(ref) | set(nouveau)):
        a, b = ref.get(k), nouveau.get(k)
        if a is None or b is None:
            ecarts.append((k, "offre", "absente" if b is None else "nouvelle", ""))
            continue
        for champ in sorted(set(a) | set(b)):
            if a.get(champ) != b.get(champ):
                ecarts.append((k, champ, a.get(champ), b.get(champ)))
    for k, champ, avant, apres in ecarts[:max_aff]:
        if isinstance(avant, str) and isinstance(apres, str) and "\n" in avant + apres:
            diff = difflib.unified_diff(avant.splitlines(), apres.splitlines(), lineterm="", n=0)
            print(f"≠ {k} · {champ}\n  " + "\n  ".join(list(diff)[2:12]))
        else:
            print(f"≠ {k} · {champ} : {avant!r} → {apres!r}")
    if len(ecarts) > max_aff:
        print(f"… et {len(ecarts) - max_aff} autre(s) écart(s)")
    return ecarts


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("action", choices=("enregistrer", "comparer"))
    ap.add_argument("reference", help="fichier JSON de reference")
    ap.add_argument("--file", help="vraie file apply_queue.json (sinon : offres fictives)")
    ap.add_argument("--profil", help="profil a utiliser (defaut : profil d'exemple)")
    ap.add_argument("--docs", type=int, default=24, help="lettres et CV complets mesures")
    ap.add_argument(
        "--moteur",
        help="dossier Scripts/ a mesurer (defaut : celui de ce depot) — "
        "pour Recherche_emploi, ses modeles de CV en dependent",
    )
    a = ap.parse_args()
    if a.moteur:
        global SCRIPTS
        SCRIPTS = Path(a.moteur).resolve()
    # BEFORE any engine import: it reads the profile when loaded.
    os.environ["PROFIL_JOBHUNTER"] = str(Path(a.profil).resolve() if a.profil else EXEMPLE)
    offres, cle = charger_jeu(a)
    mesure = mesurer(offres, cle, a.docs)
    empreinte = hashlib.sha256(json.dumps(mesure, sort_keys=True).encode()).hexdigest()[:16]
    chemin = Path(a.reference)
    if a.action == "enregistrer":
        chemin.write_text(
            json.dumps(
                {"format": VERSION_FORMAT, "empreinte": empreinte, "offres": mesure},
                ensure_ascii=False,
                indent=1,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"{len(mesure)} offres mesurées, référence écrite : {chemin} ({empreinte})")
        return 0
    ref = json.loads(chemin.read_text(encoding="utf-8"))
    ecarts = comparer(ref["offres"], mesure)
    if ecarts:
        print(
            f"\n✗ {len(ecarts)} écart(s) sur {len(mesure)} offres. Si le changement est voulu : "
            f"python outils/banc.py enregistrer {chemin}, dans le même commit."
        )
        return 1
    print(f"✓ {len(mesure)} offres, 0 écart ({empreinte})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
