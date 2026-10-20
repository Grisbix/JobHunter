@echo off
chcp 65001 >nul
cd /d "%~dp0.."
rem In lanceurs\: everything runs from the JobHunter folder, one level up.
echo === Mise a jour de JobHunter ===
echo Ton profil, ton CV, tes lettres et ton suivi ne sont jamais touches.
echo.
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
"%PY%" JobHunter.pyw maj %*
echo.
pause
