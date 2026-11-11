"""The interface's scripts share one global scope, run in index.html's order.

A function declaration is hoisted inside its own script only: a line that runs while
script N loads cannot use a function or constant of script N+1. One did when app.js
was split (ACTIONS_OUTILS.profils = gererProfils, 2026-11-11): « gererProfils is not
defined », and everything after it in the script never ran.
"""

import re

import js_app

DECLARATION = re.compile(r"^(?:async )?function\s+(\w+)|^(?:const|let|var|class)\s+(\w+)", re.M)


def test_les_scripts_existent_et_app_js_vient_en_premier():
    noms = js_app.scripts()
    assert noms[0] == "app.js" and len(noms) == len(set(noms)) > 1
    for n in noms:
        assert (js_app.STATIQUE / n).is_file(), n


def test_aucune_ligne_chargee_n_utilise_un_script_suivant():
    noms = js_app.scripts()
    textes = {n: (js_app.STATIQUE / n).read_text(encoding="utf-8") for n in noms}
    ou = {}
    for i, n in enumerate(noms):
        for m in DECLARATION.finditer(textes[n]):
            ou[m.group(1) or m.group(2)] = i
    fautes = []
    for i, n in enumerate(noms):
        for k, ligne in enumerate(textes[n].split("\n"), 1):
            # a top-level statement, not a declaration nor inside a block
            if not ligne or ligne[0] in " \t}/)]" or re.match(r"(async )?function ", ligne):
                continue
            # what an arrow function's body uses is read when it runs, not now
            maintenant = ligne.split("=>")[0]
            for ident in set(re.findall(r"\b([A-Za-z_]\w*)\b", maintenant)):
                j = ou.get(ident)
                if j is not None and j > i:
                    fautes.append(f"{n}:{k} {ident} ({noms[j]})")
    assert not fautes, fautes


def test_chaque_ecran_est_declare_une_fois():
    js = js_app.source()
    ecrans = re.findall(r"^ECRANS\.(\w+) = \{", js, re.M)
    assert len(ecrans) == len(set(ecrans)) >= 10, ecrans
