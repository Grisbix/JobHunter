#!/usr/bin/env python3
"""export_queue_csv.py — Readable backup of the queue (Excel-compatible CSV).

apply_queue.json is the ONLY store of the offers. If it is corrupted or overwritten,
there is no usable copy outside git. This script produces a CSV that opens in
Excel/LibreOffice, with rotation (keeps the last N).

Encoding: utf-8-sig (BOM) — without the BOM, Excel shows "CharlesÃ©" instead of
"Charles é" on accents.
Separator: ';' — Excel in a French locale splits on ';', not on ','.

Run:
  python JobHunter.pyw export_queue_csv                 # today's export in _exports/
  python JobHunter.pyw export_queue_csv --keep 8        # only keeps the 8 most recent
  python JobHunter.pyw export_queue_csv --out path.csv
"""

import argparse
import csv
import datetime
import importlib
import json
import sys
from pathlib import Path

from jobhunter import racine as _racine

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]  # console : TextIOWrapper

HERE = _racine.scripts()
QUEUE = HERE / "apply_queue.json"
EXPORTS = HERE / "_exports"

# (queue key, CSV header) — columns useful for human review
COLS = [
    ("entreprise", "Entreprise"),
    ("poste", "Poste"),
    ("domaine", "Domaine"),
    ("fit", "Fit"),
    ("ats_pct", "ATS%"),
    ("exp_requise", "Exp. exigée"),
    ("contrat", "Contrat"),
    ("localisation", "Lieu"),
    ("teletravail", "Télétravail"),
    ("salaire", "Salaire"),
    ("priorite", "Priorité"),
    ("canal", "Canal"),
    ("url_type", "Type lien"),
    ("link_status", "État lien"),
    ("ls_check", "Vérifié le"),
    ("process", "Date offre"),
    ("source", "Source"),
    ("statut", "Statut scan"),
    ("cv", "CV"),
    ("lettre", "Lettre"),
    ("url", "Lien"),
]


def rows(q, suivi):
    for o in q:
        r = {}
        for k, label in COLS:
            v = o.get(k)
            if isinstance(v, (dict, list)):
                v = json.dumps(v, ensure_ascii=False)
            r[label] = "" if v is None else str(v)
        key = f"{o.get('entreprise', '')}|{o.get('poste', '')}"
        s = suivi.get(key) or {}
        r["Suivi statut"] = str(s.get("statut") or "")
        r["Suivi note"] = str(s.get("note") or "")
        r["Suivi date"] = str(s.get("date") or "")
        yield r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="chemin du CSV (défaut : _exports/queue_AAAA-MM-JJ.csv)")
    ap.add_argument("--keep", type=int, default=8, help="nb d'exports à conserver (0 = tous)")
    a = ap.parse_args()

    if not QUEUE.exists():
        print("! apply_queue.json introuvable")
        return 1
    q = importlib.import_module("jobhunter.stockage.file").charger(QUEUE, descriptions=False)

    suivi = {}
    sp = HERE / "suivi.json"
    if sp.exists():
        try:
            suivi = json.loads(sp.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  (suivi.json illisible : {type(e).__name__} — export sans le suivi)")

    out = Path(a.out) if a.out else EXPORTS / f"queue_{datetime.date.today():%Y-%m-%d}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)

    head = [label for _, label in COLS] + ["Suivi statut", "Suivi note", "Suivi date"]
    # written next to it then replaced: a crash in progress does not overwrite the previous export
    tmp = out.with_suffix(".csv.tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=head, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        n = 0
        for r in rows(q, suivi):
            w.writerow(r)
            n += 1
    tmp.replace(out)
    print(f"=== {n} offres -> {out} ({out.stat().st_size // 1024} Ko) ===")

    if a.keep > 0:
        olds = sorted(EXPORTS.glob("queue_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
        for p in olds[a.keep :]:
            p.unlink()
            print(f"  rotation : {p.name} supprimé")
    return 0


if __name__ == "__main__":
    sys.exit(main())
