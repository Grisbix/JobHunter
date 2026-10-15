#!/usr/bin/env bash
# Installation de JobHunter (macOS, Linux). Equivalent de installer.bat.
set -e
cd "$(dirname "$0")"
echo "=== Installation de JobHunter ==="
PY=$(command -v python3 || command -v python || true)
if [ -z "$PY" ]; then
  echo "Python est introuvable. Installe Python 3.12 ou plus recent :"
  echo "  macOS : https://www.python.org/downloads/  (ou : brew install python@3.12)"
  echo "  Linux : sudo apt install python3 python3-pip python3-tk  (ou l'equivalent de ta distribution)"
  exit 1
fi
if ! "$PY" -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)"; then
  echo "Python 3.12 ou plus recent est necessaire. Version actuelle : $("$PY" --version)"
  exit 1
fi
"$PY" -m pip install -r requirements.txt
"$PY" -m playwright install chromium
echo
echo "Installation terminee. Depose ton CV dans Mon_CV puis lance ./lancer.sh"
echo "Ensuite : ./planifier.sh lance la collecte chaque matin, ./mettre_a_jour.sh recupere les nouveautes."
