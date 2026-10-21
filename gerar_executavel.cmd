@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
    echo Instale Python 3.11 x64 com Tcl/Tk e o Python Launcher antes de gerar o pacote.
    pause
    exit /b 1
)
if not exist ".venv-build\Scripts\python.exe" (
    py -3.11 -m venv .venv-build
    if errorlevel 1 goto falha
)
".venv-build\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 goto falha
".venv-build\Scripts\python.exe" -m unittest discover -s tests -q
if errorlevel 1 goto falha
".venv-build\Scripts\python.exe" tools\gerar_executavel.py
if errorlevel 1 goto falha
echo.
echo Pacote criado em dist\GestaoDaFeira-Windows-x64.zip
pause
exit /b 0
:falha
echo.
echo Nao foi possivel gerar e validar o executavel. Veja o erro acima.
pause
exit /b 1
