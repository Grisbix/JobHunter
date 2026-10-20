"""Entry point of the compiled executables: JobHunter.exe and jobhunter-cli.exe.

All the work is in jobhunter.frozen; this file only exists because PyInstaller
starts from a script.
"""

from jobhunter.frozen import main

raise SystemExit(main())
