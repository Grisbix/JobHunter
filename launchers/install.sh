#!/usr/bin/env bash
# JobHunter installation (macOS, Linux). Equivalent of install.bat.
set -e
cd "$(dirname "$0")/.."
# In launchers/: everything runs from the JobHunter folder, one level up.
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
# The window needs Tk, packaged apart on Linux and with Homebrew: without it the install
# said "terminee" and the app stopped on "No module named 'tkinter'".
SANS_TK=""
if ! "$PY" -c "import tkinter" 2>/dev/null; then
  SANS_TK="Il manque Tk a Python : la fenetre ne s'ouvrira pas (la collecte, si).
  Linux : sudo apt install python3-tk  (ou l'equivalent de ta distribution)
  macOS : brew install python-tk@3.12  (ou le Python de python.org, qui l'inclut)"
  echo "$SANS_TK"
fi
# A Python environment of JobHunter's own, in .venv: the installed packages do not
# touch the computer's Python. The other scripts use it if it exists.
if [ ! -x .venv/bin/python ]; then
  echo "Creation de l'environnement Python de JobHunter dans .venv ..."
  "$PY" -m venv .venv || {
    echo "Echec de venv. Sous Debian/Ubuntu : sudo apt install python3-venv, puis relance."
    exit 1
  }
fi
PY=.venv/bin/python
"$PY" -m pip install -r requirements.txt
"$PY" -m playwright install chromium
# Fingerprint of the files as installed: the update will recognise your changes.
"$PY" JobHunter.pyw update --initialiser
echo
echo "Installation terminee. Depose ton CV dans My_CV (ou glisse-le sur la fenetre) puis lance ./launchers/start.sh"
[ -n "$SANS_TK" ] && { echo; echo "ATTENTION : $SANS_TK"; }
echo "Ensuite : ./launchers/schedule.sh lance la collecte chaque matin, ./launchers/update.sh recupere les nouveautes."
