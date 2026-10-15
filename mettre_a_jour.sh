#!/usr/bin/env bash
# Mise a jour de JobHunter (macOS, Linux). Equivalent de mettre_a_jour.bat.
cd "$(dirname "$0")"
echo "=== Mise a jour de JobHunter ==="
echo "Ton profil, ton CV, tes lettres et ton suivi ne sont jamais touches."
echo
"$(command -v python3 || command -v python)" Scripts/mise_a_jour.py "$@"
