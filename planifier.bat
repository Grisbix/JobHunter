@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem Cree (ou supprime) la tache planifiee qui lance la collecte chaque matin.
rem   planifier.bat            -> tous les jours a 08:00
rem   planifier.bat 07:30      -> tous les jours a 07:30
rem   planifier.bat supprimer  -> retire la tache
set "TACHE=JobHunter - collecte quotidienne"

if /i "%~1"=="supprimer" (
  schtasks /Delete /TN "%TACHE%" /F
  pause
  exit /b
)

set "HEURE=%~1"
if "%HEURE%"=="" set "HEURE=08:00"

set "PY="
for /f "delims=" %%p in ('where python 2^>nul') do if not defined PY set "PY=%%p"
if not defined PY (
  echo Python est introuvable : lance d'abord installer.bat.
  pause
  exit /b 1
)
if not exist "profil\profil.json" (
  echo Pas encore de profil : lance d'abord lancer.bat.
  pause
  exit /b 1
)

schtasks /Create /F /SC DAILY /ST %HEURE% /TN "%TACHE%" /TR "\"%PY%\" \"%~dp0Scripts\pipeline_quotidien.py\""
if errorlevel 1 (
  echo La tache n'a pas pu etre creee.
  pause
  exit /b 1
)
echo.
echo Tache creee : la collecte tournera chaque jour a %HEURE% si l'ordinateur est allume.
echo Journaux : Scripts\_logs\  - Pour la retirer : planifier.bat supprimer
pause
