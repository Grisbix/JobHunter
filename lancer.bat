@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "profil\profil.json" goto app
set "CV="
for %%f in ("Mon_CV\*.docx" "Mon_CV\*.pdf") do if not defined CV set "CV=%%f"
if not defined CV (
  echo Aucun CV dans Mon_CV. Depose ton CV .docx ou .pdf dans ce dossier, puis relance.
  pause
  exit /b 1
)
echo Premier lancement : creation du profil a partir de %CV%
python Scripts\premier_lancement.py "%CV%" || (pause & exit /b 1)
echo.
echo Profil cree dans profil\profil.json. Relis-le, ou demande a Claude Code : /configurer-profil
pause
:app
start "" pythonw JobHunter.pyw
