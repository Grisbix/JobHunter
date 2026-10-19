"""Point d'entrée des exécutables compilés : JobHunter.exe et jobhunter-cli.exe.

Tout le travail est dans jobhunter.gele ; ce fichier n'existe que parce que PyInstaller
part d'un script.
"""

from jobhunter.gele import main

raise SystemExit(main())
