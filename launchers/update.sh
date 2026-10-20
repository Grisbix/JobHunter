#!/usr/bin/env bash
# JobHunter update (macOS, Linux). Equivalent of update.bat.
cd "$(dirname "$0")/.."
# In launchers/: everything runs from the JobHunter folder, one level up.
echo "=== Mise a jour de JobHunter ==="
echo "Ton profil, ton CV, tes lettres et ton suivi ne sont jamais touches."
echo
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=$(command -v python3 || command -v python); fi
"$PY" JobHunter.pyw update "$@"
