#!/usr/bin/env bash
# Ouvre JobHunter (macOS, Linux). La premiere fois, cree le profil depuis le CV de Mon_CV.
cd "$(dirname "$0")"
PY=$(command -v python3 || command -v python)
if [ ! -f profil/profil.json ]; then
  CV=$(ls Mon_CV/*.docx Mon_CV/*.pdf 2>/dev/null | head -n 1)
  if [ -z "$CV" ]; then
    echo "Aucun CV dans Mon_CV. Depose ton CV .docx ou .pdf dans ce dossier, puis relance."
    exit 1
  fi
  echo "Premier lancement : creation du profil a partir de $CV"
  "$PY" JobHunter.pyw profil "$CV" || exit 1
  echo
  echo "Profil cree dans profil/profil.json. Relis-le, ou demande a Claude Code : /configurer-profil"
fi
exec "$PY" JobHunter.pyw
