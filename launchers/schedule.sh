#!/usr/bin/env bash
# Daily collection through cron (macOS, Linux). Equivalent of schedule.bat.
#   ./schedule.sh            -> every day at 08:00
#   ./schedule.sh 07:30      -> every day at 07:30
#   ./schedule.sh supprimer  -> removes the line
cd "$(dirname "$0")/.."
# In launchers/: everything runs from the JobHunter folder, one level up.
DOSSIER=$(pwd)
MARQUE="# JobHunter - collecte quotidienne"
ACTUEL=$(crontab -l 2>/dev/null | grep -v -F "$MARQUE" || true)

if [ "$1" = "supprimer" ]; then
  printf '%s\n' "$ACTUEL" | crontab -
  echo "Collecte quotidienne retiree."
  exit 0
fi
if [ ! -f profile/profile.json ] && [ ! -f profil/profil.json ]; then
  echo "Pas encore de profil : lance d'abord ./launchers/start.sh"
  exit 1
fi
HEURE=${1:-08:00}
H=${HEURE%%:*}; M=${HEURE##*:}
if [ -x .venv/bin/python ]; then PY="$DOSSIER/.venv/bin/python"; else PY=$(command -v python3 || command -v python); fi
LIGNE="$((10#$M)) $((10#$H)) * * * cd \"$DOSSIER\" && \"$PY\" JobHunter.pyw pipeline >/dev/null 2>&1 $MARQUE"
printf '%s\n%s\n' "$ACTUEL" "$LIGNE" | sed '/^$/d' | crontab -
echo "Collecte planifiee chaque jour a $HEURE (si l'ordinateur est allume)."
echo "Journaux : data/_logs/  -  Pour la retirer : ./launchers/schedule.sh supprimer"
