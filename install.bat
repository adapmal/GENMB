@echo off
setlocal
cd /d "%~dp0"

echo.
echo ========================================
echo Instalando o GENMB
echo ========================================
echo.

where py >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python nao foi encontrado.
    echo Instale o Python 3.11 ou mais recente e marque "Add Python to PATH".
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual...
    py -m venv .venv
    if errorlevel 1 goto :error
)

echo Atualizando o pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :error

echo Instalando dependencias...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo Instalando o Chromium do Playwright...
".venv\Scripts\python.exe" -m playwright install chromium
if errorlevel 1 goto :error

echo.
echo Instalacao concluida com sucesso.
pause
exit /b 0

:error
echo.
echo A instalacao falhou. Veja a mensagem acima.
pause
exit /b 1