@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Mise a jour de JobHunter ===
echo Ton profil, ton CV, tes lettres et ton suivi ne sont jamais touches.
echo.
python Scripts\mise_a_jour.py %*
echo.
pause
