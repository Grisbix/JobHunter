#!/usr/bin/env bash
# Opens JobHunter (macOS, Linux). The first time, creates the profile from the CV in My_CV.
cd "$(dirname "$0")/.."
# In launchers/: everything runs from the JobHunter folder, one level up.
# install.sh's environment if it exists, otherwise the computer's Python.
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=$(command -v python3 || command -v python); fi
# 3.0 layout (profile/, My_CV/) or 2.x (profil/, Mon_CV/), until the migration.
if [ ! -f profile/profile.json ] && [ ! -f profil/profil.json ]; then
  CV=$(ls My_CV/*.docx My_CV/*.pdf Mon_CV/*.docx Mon_CV/*.pdf 2>/dev/null | head -n 1)
  if [ -z "$CV" ]; then
    echo "Aucun CV dans My_CV. Depose ton CV .docx ou .pdf dans ce dossier, puis relance."
    exit 1
  fi
  echo "Premier lancement : creation du profil a partir de $CV"
  "$PY" JobHunter.pyw profile "$CV" || exit 1
  echo
  echo "Profil cree. Dans l'app : Ma recherche (mots-cles, villes), Profil (competences), puis Actualiser les offres."
fi
exec "$PY" JobHunter.pyw
