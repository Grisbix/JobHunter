@echo off
chcp 65001 >nul
cd /d "%~dp0.."
rem In launchers\: everything runs from the JobHunter folder, one level up.
rem install.bat's environment if it exists, otherwise the computer's Python.
set "PY=python"
set "PYW=pythonw"
if exist ".venv\Scripts\python.exe" (
  set "PY=.venv\Scripts\python.exe"
  set "PYW=.venv\Scripts\pythonw.exe"
)
rem 3.0 layout (profile\, My_CV\) or 2.x (profil\, Mon_CV\), until the migration.
if exist "profile\profile.json" goto app
if exist "profil\profil.json" goto app
set "CV="
for %%f in ("My_CV\*.docx" "My_CV\*.pdf" "Mon_CV\*.docx" "Mon_CV\*.pdf") do if not defined CV set "CV=%%f"
if not defined CV (
  echo Aucun CV dans My_CV. Depose ton CV .docx ou .pdf dans ce dossier, puis relance.
  pause
  exit /b 1
)
echo Premier lancement : creation du profil a partir de %CV%
"%PY%" JobHunter.pyw profile "%CV%" || (pause & exit /b 1)
echo.
echo Profil cree dans profile\profile.json. Relis-le, ou demande a Claude Code : /configure-profile
pause
:app
start "" "%PYW%" JobHunter.pyw
