@echo off
chcp 65001 >nul
cd /d "%~dp0.."
rem In launchers\: everything runs from the JobHunter folder, one level up.
echo === Installation de JobHunter ===
where python >nul 2>nul
if not errorlevel 1 goto python_ok
echo Python est introuvable.
where winget >nul 2>nul
if errorlevel 1 goto python_manuel
choice /c ON /m "L'installer maintenant (Python 3.12, pour ton compte, via winget)"
if errorlevel 2 goto python_manuel
rem winget displays its own terms: you are the one who accepts them.
winget install -e --id Python.Python.3.12 --scope user
if errorlevel 1 goto python_manuel
echo.
echo Python est installe. FERME cette fenetre et relance install.bat
echo (la nouvelle fenetre saura ou trouver Python).
pause
exit /b 0
:python_manuel
echo Installe Python depuis https://www.python.org/downloads/
echo en cochant "Add Python to PATH", puis relance install.bat.
pause
exit /b 1
:python_ok
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)"
if errorlevel 1 (
  echo Python 3.12 ou plus recent est necessaire. Version actuelle :
  python --version
  echo Installe la derniere version depuis https://www.python.org/downloads/
  pause
  exit /b 1
)
rem A Python environment of JobHunter's own, in .venv: the installed packages
rem do not touch the computer's Python. The other .bat files use it if it exists.
if not exist ".venv\Scripts\python.exe" (
  echo Creation de l'environnement Python de JobHunter dans .venv ...
  python -m venv .venv || goto erreur
)
set "PY=.venv\Scripts\python.exe"
"%PY%" -m pip install -r requirements.txt || goto erreur
"%PY%" -m playwright install chromium || goto erreur
rem Fingerprint of the files as installed: the update will recognise your changes.
"%PY%" JobHunter.pyw update --initialiser
echo.
echo Installation terminee. Depose ton CV dans My_CV (ou glisse-le sur la fenetre) puis lance start.bat.
echo Ensuite : schedule.bat lance la collecte chaque matin, update.bat recupere les nouveautes.
pause
exit /b 0
:erreur
echo Une etape a echoue : lis le message ci-dessus.
pause
exit /b 1
