@echo off
setlocal

set "VENV_DIR=.venv"

if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo [1/4] Criando ambiente virtual em %VENV_DIR%...
  py -m venv "%VENV_DIR%"
  if errorlevel 1 goto :error
)

echo [2/4] Ativando ambiente virtual...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 goto :error

echo [3/4] Instalando dependencias...
python -m pip install --upgrade pip
if errorlevel 1 goto :error
pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :error

echo [4/4] Gerando executavel DEMO...
py -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --name TaxDiagnosticDemo ^
  --collect-data streamlit ^
  --collect-submodules streamlit ^
  --collect-data reportlab ^
  --collect-submodules reportlab ^
  --add-data "app.py;." ^
  --add-data "rulesets;rulesets" ^
  run_demo.py
if errorlevel 1 goto :error

echo.
echo Build concluido com sucesso.
echo Executavel: dist\TaxDiagnosticDemo.exe
exit /b 0

:error
echo.
echo Build falhou.
exit /b 1
