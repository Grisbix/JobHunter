"""Entry point of the compiled executables: JobHunter.exe and jobhunter-cli.exe.

All the work is in jobhunter.gele; this file only exists because PyInstaller
starts from a script.
"""

from jobhunter.gele import main

raise SystemExit(main())
