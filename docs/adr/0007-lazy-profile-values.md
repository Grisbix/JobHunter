# 0007 — What comes from the profile is computed on first read

**Status**: accepted, 2026-10-18 (phase 4 of the plan).

## Context

About a hundred module constants were computed at load time from the profile
(title-filter patterns, scoring axes and caps, letter and
message texts, sectors) or from `Scripts/chemins.json` (document folders). Importing
`jobhunter.sources.linkedin` therefore read the profile; a test could not switch
profile without reloading every module; `premier_lancement` changed profile
midway and kept the values of the old one.

## Decision

- Each module concerned declares these values as **factories** in its `_PARESSEUX`
  dictionary, and its module-level `__getattr__` (PEP 562) computes them on first
  read and then stores them in the module (`jobhunter.paresseux`).
- Inside the module, the code reads them as `_ici.NOM` (`_ici` = the module itself): a bare
  global name does not go through `__getattr__`. Other modules read `module.NOM` or
  `from module import NOM` inside a function; a module-level `from module import NOM` is
  replaced there by a factory that re-reads the name on first use.
- The `Scripts/x.py` facades launch their module through `runpy.run_module(...,
  alter_sys=True)`: without that, `sys.modules["__main__"]` remains the facade and `_ici`
  would point to it.
- `profil.utiliser(donnees)` injects an in-memory profile; `profil.recharger(fichier)`
  goes back to the file. Both forget the values already computed.
- Names and values do not change: `monkeypatch.setattr(module, "NOM", ...)` and
  the facades ([ADR 0001](0001-facade-aliases.md)) keep working. The facade
  knows the lazy names of its submodules.
- The transformation was GENERATED from the syntax tree, then checked by the bench
  ([ADR 0006](0006-non-regression-bench.md)): 0 differences.

## Consequences

Loading the whole engine reads no file, writes nothing and does not go out on the network;
`tests/test_import_side_effects.py` checks it (ratchet). A new constant drawn from the
profile is written `_PARESSEUX["NOM"] = lambda: ...` and read `_ici.NOM`; a read of the
profile at module level would make this test fail.

mypy sees these values as `Any`: that is the price of keeping the names compatible. Replacing
them with typed configuration objects (`Profil`) is possible later, without
touching outside callers.
