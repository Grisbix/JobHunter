#!/usr/bin/env bash
# Mise a jour de JobHunter (macOS, Linux). Equivalent de mettre_a_jour.bat.
cd "$(dirname "$0")"
echo "=== Mise a jour de JobHunter ==="
echo "Ton profil, ton CV, tes lettres et ton suivi ne sont jamais touches."
echo
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=$(command -v python3 || command -v python); fi
"$PY" JobHunter.pyw maj "$@"
