"""JobHunter — the engine, as a package.

Phase 3 of the plan (docs/plan-professionnalisation.md): the code of Scripts/ moves
here module by module. During the transition, each old module of Scripts/ stays in
place as a FACADE: it registers itself under its old name pointing to the new module, so
that `import queue_io` and `jobhunter.stockage.file` are the SAME module object
(a `monkeypatch.setattr(queue_io, ...)` therefore acts on the real code).
"""
