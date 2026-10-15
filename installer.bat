@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Installation de JobHunter ===
where python >nul 2>nul
if not errorlevel 1 goto python_ok
echo Python est introuvable.
where winget >nul 2>nul
if errorlevel 1 goto python_manuel
choice /c ON /m "L'installer maintenant (Python 3.12, pour ton compte, via winget)"
if errorlevel 2 goto python_manuel
rem winget affiche lui-meme ses conditions : c'est toi qui les acceptes.
winget install -e --id Python.Python.3.12 --scope user
if errorlevel 1 goto python_manuel
echo.
echo Python est installe. FERME cette fenetre et relance installer.bat
echo (la nouvelle fenetre saura ou trouver Python).
pause
exit /b 0
:python_manuel
echo Installe Python depuis https://www.python.org/downloads/
echo en cochant "Add Python to PATH", puis relance installer.bat.
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
python -m pip install -r requirements.txt || goto erreur
python -m playwright install chromium || goto erreur
rem Empreinte des fichiers tels qu'installes : la mise a jour reconnaitra tes modifications.
python Scripts\mise_a_jour.py --initialiser
echo.
echo Installation terminee. Depose ton CV dans Mon_CV puis lance lancer.bat.
echo Ensuite : planifier.bat lance la collecte chaque matin, mettre_a_jour.bat recupere les nouveautes.
pause
exit /b 0
:erreur
echo Une etape a echoue : lis le message ci-dessus.
pause
exit /b 1
