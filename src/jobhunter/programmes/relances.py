#!/usr/bin/env python3
"""
relances.py — Generates personalised D+7 / D+10 follow-up emails per offer.

Reads apply_queue.json, takes the 'prio' offers (or --all), writes a follow-up .txt
ready to copy and paste into Lettres/Relances/. A follow-up roughly doubles the
response rate.

Run: python JobHunter.pyw relances            # all the 'prio' offers
     python JobHunter.pyw relances --company Amundi
     python JobHunter.pyw relances --jours 10 # D+10 variant (default D+7)
"""

import argparse
import importlib
import json
import re
import sys
from pathlib import Path

from jobhunter import racine as _racine

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # console : TextIOWrapper
except Exception:
    pass

ROOT = _racine.racine()
Q = ROOT / "Scripts" / "apply_queue.json"
OUT = ROOT / "Lettres" / "Relances"
OUT.mkdir(parents=True, exist_ok=True)

from jobhunter import profil as _P

NOM = _P.identite()["nom"]
# Agreements and profile summary: "— diplome, stage… —" comes from message.diplome_fr.
_DIPLOME = (_P.get("message.diplome_fr", "") or "").strip()
_ACCORDS = {
    "motive": _P.accord("motivé", "motivée"),
    "ravi": _P.accord("ravi", "ravie"),
    "heureux": _P.accord("heureux", "heureuse"),
    "resume": f" — {_DIPLOME} —" if _DIPLOME else "",
}
_CONTACT = " · ".join(v for v in (_P.identite()["email"], _P.identite()["tel"]) if v)
SIGNATURE = f"{NOM}\n{_CONTACT}" if _CONTACT else NOM

TPL_J7 = """Objet : Relance — candidature {role} chez {company}

Madame, Monsieur,

Je me permets de revenir vers vous concernant ma candidature au poste {de_role}, transmise il y a une semaine.

Toujours vivement {motive} par ce poste et par {company}, je reste à votre entière disposition pour un échange. Je serais {ravi} de préciser en quoi mon profil{resume} répond à vos besoins.

Je vous remercie par avance de l'attention portée à ma démarche.

Bien cordialement,
{sign}
"""

TPL_J10 = """Objet : Suivi de candidature — {role} ({company})

Madame, Monsieur,

Sauf erreur de ma part, ma candidature au poste {de_role} n'a pas encore pu être étudiée. Je me permets donc une dernière relance.

Mon intérêt pour {company} reste entier. Si le poste est toujours ouvert, je serais {heureux} de vous rencontrer ; s'il est pourvu, un simple retour me permettrait d'orienter mes recherches.

Je vous remercie de votre temps.

Bien cordialement,
{sign}
"""


def de(mot):
    mot = (mot or "ce poste").strip()
    return ("d'" + mot) if mot[:1].lower() in "aàâäeéèêëiîïoôöuùûüyh" else ("de " + mot)


SUIVI = ROOT / "Scripts" / "suivi.json"
RELANCE_STATUTS = ("postulé", "relancé")


def _oid(o):
    return f"{(o.get('entreprise') or '').strip()}|{(o.get('poste') or '').strip()}"


def a_relancer(days=10):
    """Candidatures « postulé/relancé » depuis ≥ days jours (suivi.json).
    Retour [(offre, statut, date, âge_jours)] du plus vieux au plus récent."""
    from datetime import date, datetime

    q = json.load(open(Q, encoding="utf-8"))
    try:
        s = importlib.import_module("jobhunter.stockage.suivi").charger(SUIVI)
    except Exception:
        s = {}
    today = date.today()
    out = []
    for o in q:
        sv = s.get(_oid(o), {})
        if sv.get("s") not in RELANCE_STATUTS:
            continue
        try:
            d = datetime.strptime(sv.get("d", ""), "%Y-%m-%d").date()
        except Exception:
            continue
        age = (today - d).days
        if age >= days:
            out.append((o, sv["s"], sv.get("d"), age))
    out.sort(key=lambda t: -t[3])
    return out


def chemin_brouillon(o, j, dossier=None):
    safe = re.sub(r"[^\w\-]", "_", f"{o['entreprise']}_{o['poste'] or 'le poste proposé'}")[
        :60
    ].strip("_")
    return Path(dossier or OUT) / f"Relance_J{j}_{safe}.txt"


def ecrire_brouillon(o, j=7, dossier=None):
    """Écrit le .txt de relance d'une offre et rend son chemin. N'ouvre rien."""
    comp, role = o["entreprise"], o["poste"] or "le poste proposé"
    tpl = TPL_J7 if j == 7 else TPL_J10
    txt = tpl.format(company=comp, role=role, de_role=de(role), sign=SIGNATURE, **_ACCORDS)
    f = chemin_brouillon(o, j, dossier)
    f.write_text(txt, encoding="utf-8")
    return f


def make_draft(key, j=7, open_mailto=True):
    """Écrit le brouillon .txt + ouvre mailto: (TON client mail — TU envoies)."""
    q = json.load(open(Q, encoding="utf-8"))
    o = next((x for x in q if _oid(x) == key), None)
    if o is None:
        print(f"offre introuvable : {key}")
        return False
    f = ecrire_brouillon(o, j)
    txt = f.read_text(encoding="utf-8")
    print(f"📝 brouillon : {f}")
    if open_mailto:
        from urllib.parse import quote

        sujet, corps = txt.split("\n", 1)
        import webbrowser

        webbrowser.open(
            f"mailto:?subject={quote(sujet.replace('Objet : ', ''))}&body={quote(corps.strip())}"
        )
        print("📧 client mail ouvert (destinataire à compléter) — TU envoies.")
    return True


def preparer_brouillons(lst, dossier=None):
    """Drafts of the week for the Windows task `Relances` (2026-10-08).

    Returns a Markdown summary that publier.py stores in the vault. Sends nothing,
    opens no mail client, marks nothing in the tracking: the user reviews, sends
    themselves, then runs --mark. An application already followed up once receives
    the D+10 template ("dernière relance"); a draft already present is not
    rewritten, so as not to overwrite a version edited by hand.
    """
    from datetime import date

    l = [f"# Relances à envoyer — {date.today().isoformat()}", ""]
    if not lst:
        l.append("Rien à relancer : aucune candidature sans réponse depuis assez longtemps.")
        return "\n".join(l)
    l += [
        f"**{len(lst)} candidature(s)** sans réponse. Brouillons dans `Lettres/Relances/` : "
        "**rien n'est envoyé**, le destinataire est à compléter.",
        "",
        "| Âge | Entreprise | Poste | Modèle | Brouillon |",
        "|---|---|---|---|---|",
    ]
    for o, st, d, age in lst:
        j = 10 if st == "relancé" else 7
        f = chemin_brouillon(o, j, dossier)
        etat = "déjà prêt" if f.exists() else "nouveau"
        if etat == "nouveau":
            ecrire_brouillon(o, j, dossier)
        l.append(f"| {age} j | {o['entreprise']} | {o['poste']} | J+{j} | `{f.name}` ({etat}) |")
    l += ["", 'Après envoi : `python JobHunter.pyw relances --mark "Entreprise|Poste"`.']
    return "\n".join(l)


def mark(key):
    """Records the follow-up. Under lock: the app writes the same file.

    Reading then writing without a lock is what made applications disappear — the
    app rewrote its whole snapshot over it. `suivi_io` re-reads the disk inside the
    lock, so each keeps the other's work.
    """
    from datetime import date

    from jobhunter.stockage import suivi as suivi_io

    def _f(s):
        rec = dict(s.get(key, {}))
        rec["s"] = "relancé"
        rec["d"] = date.today().isoformat()
        s[key] = rec

    try:
        suivi_io.modifier(_f, SUIVI)
    except suivi_io.VerrouIndisponible:
        print(f"✗ suivi.json occupé par un autre programme — {key} NON marqué.")
        return False
    print(f"🔁 statut relancé : {key}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=10, help="seuil jours sans réponse (défaut 10)")
    ap.add_argument("--jours", type=int, default=7, choices=[7, 10], help="template J+7 ou J+10")
    ap.add_argument("--draft", help='"Entreprise|Poste" → brouillon .txt + mailto (TU envoies)')
    ap.add_argument("--mark", help='"Entreprise|Poste" → statut relancé (date du jour)')
    ap.add_argument("--company", help="mode legacy : brouillons pour une entreprise")
    ap.add_argument(
        "--brouillons",
        action="store_true",
        help="brouillons .txt de toutes les relances dues + bilan Markdown (n'ouvre et n'envoie rien)",
    )
    a = ap.parse_args()

    if a.brouillons:
        print(preparer_brouillons(a_relancer(a.days)))
        return
    if a.draft:
        make_draft(a.draft, j=a.jours)
        return
    if a.mark:
        mark(a.mark)
        return
    if a.company:  # legacy
        q = json.load(open(Q, encoding="utf-8"))
        for x in [x for x in q if a.company.lower() in (x["entreprise"] or "").lower()]:
            make_draft(_oid(x), j=a.jours, open_mailto=False)
        return
    # default: lists what is TO FOLLOW UP according to the tracking
    lst = a_relancer(a.days)
    if not lst:
        print(f"Rien à relancer (aucune candidature « postulé » depuis ≥ {a.days} j).")
        return
    print(f"🔔 {len(lst)} candidature(s) à relancer (≥ {a.days} j) :")
    for o, st, d, age in lst:
        print(f"  {age:3} j  [{st}] {o['entreprise'][:28]} — {o['poste'][:45]}")
    print('\n→ python JobHunter.pyw relances --draft "Entreprise|Poste"   (brouillon + mailto)')
    print('→ python JobHunter.pyw relances --mark  "Entreprise|Poste"   (statut relancé)')


if __name__ == "__main__":
    main()
