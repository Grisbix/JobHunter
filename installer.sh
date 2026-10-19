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
# Un environnement Python propre a JobHunter, dans .venv : les paquets installes ne
# touchent pas au Python de l'ordinateur. Les autres scripts l'utilisent s'il existe.
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
# Empreinte des fichiers tels qu'installes : la mise a jour reconnaitra tes modifications.
"$PY" JobHunter.pyw maj --initialiser
echo
echo "Installation terminee. Depose ton CV dans Mon_CV puis lance ./lancer.sh"
echo "Ensuite : ./planifier.sh lance la collecte chaque matin, ./mettre_a_jour.sh recupere les nouveautes."
