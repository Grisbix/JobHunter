#!/usr/bin/env bash
# Collecte quotidienne via cron (macOS, Linux). Equivalent de planifier.bat.
#   ./planifier.sh            -> tous les jours a 08:00
#   ./planifier.sh 07:30      -> tous les jours a 07:30
#   ./planifier.sh supprimer  -> retire la ligne
cd "$(dirname "$0")"
DOSSIER=$(pwd)
MARQUE="# JobHunter - collecte quotidienne"
ACTUEL=$(crontab -l 2>/dev/null | grep -v -F "$MARQUE" || true)

if [ "$1" = "supprimer" ]; then
  printf '%s\n' "$ACTUEL" | crontab -
  echo "Collecte quotidienne retiree."
  exit 0
fi
if [ ! -f profil/profil.json ]; then
  echo "Pas encore de profil : lance d'abord ./lancer.sh"
  exit 1
fi
HEURE=${1:-08:00}
H=${HEURE%%:*}; M=${HEURE##*:}
PY=$(command -v python3 || command -v python)
LIGNE="$((10#$M)) $((10#$H)) * * * cd \"$DOSSIER\" && \"$PY\" Scripts/pipeline_quotidien.py >/dev/null 2>&1 $MARQUE"
printf '%s\n%s\n' "$ACTUEL" "$LIGNE" | sed '/^$/d' | crontab -
echo "Collecte planifiee chaque jour a $HEURE (si l'ordinateur est allume)."
echo "Journaux : Scripts/_logs/  -  Pour la retirer : ./planifier.sh supprimer"
