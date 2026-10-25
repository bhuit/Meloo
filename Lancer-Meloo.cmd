@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0dist\Zeste\Meloo.exe" (
  start "" "%~dp0dist\Zeste\Meloo.exe" %*
  exit /b
)
if exist "%~dp0.venv\Scripts\pythonw.exe" (
  start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0main.py" %*
  exit /b
)
echo Distribution absente. Consultez README.txt pour installer les dependances ou reconstruire le portable.
pause
