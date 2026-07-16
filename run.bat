@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo O ambiente do GENMB ainda nao foi instalado.
    echo Execute primeiro o arquivo install.bat.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" app.py

if errorlevel 1 (
    echo.
    echo O GENMB foi encerrado com erro.
    pause
)