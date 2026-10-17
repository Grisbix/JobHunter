"""JobHunter — le moteur, en paquet.

Phase 3 du plan (docs/plan-professionnalisation.md) : le code de Scripts/ migre ici
module par module. Pendant la transition, chaque ancien module de Scripts/ reste en
place comme FACADE : il s'enregistre sous son ancien nom vers le nouveau module, si
bien que `import queue_io` et `jobhunter.stockage.file` sont le MEME objet module
(un `monkeypatch.setattr(queue_io, ...)` agit donc bien sur le code reel).
"""
