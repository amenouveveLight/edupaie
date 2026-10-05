@echo off
rem ============================================================
rem  EduPaie - build one-click de l'executable Windows
rem  Depuis la racine du projet :  build.bat
rem ============================================================
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else if exist "env\Scripts\activate.bat" (
    call "env\Scripts\activate.bat"
)

python -m PyInstaller --noconfirm --clean edupaie.spec
if errorlevel 1 goto :error

echo.
echo Executable : dist\EduPaie.exe
pause
exit /b 0

:error
echo.
echo Build en echec - verifier les messages ci-dessus.
pause
exit /b 1
