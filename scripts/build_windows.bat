@echo off
REM Build a standalone Windows executable: dist\bro.exe
setlocal EnableExtensions
set "ROOT=%~dp0.."
cd /d "%ROOT%"

if not exist "dist" mkdir dist

echo ==^> bro Windows exe build
echo Root: %CD%

if exist "%ROOT%\.venv\Scripts\python.exe" (
  set "PY=%ROOT%\.venv\Scripts\python.exe"
) else (
  set "PY=python"
)

echo ==^> Ensuring PyInstaller
"%PY%" -m pip install -q "pyinstaller>=6.0"
if errorlevel 1 exit /b 1

echo ==^> Building onefile exe (bro.exe)
"%PY%" -m PyInstaller --noconfirm --clean --distpath dist --workpath build\pyinstaller bro.spec
if errorlevel 1 exit /b 1

REM Convenience launcher next to the exe
(
  echo @echo off
  echo setlocal
  echo set "DIR=%%~dp0"
  echo if exist "%%CD%%\.env" ^(
  echo   for /f "usebackq eol=# tokens=1,* delims==" %%%%A in ^("%%CD%%\.env"^) do if not "%%%%A"=="" if not "%%%%B"=="" set "%%%%A=%%%%B"
  echo ^) else if exist "%%DIR%%.env" ^(
  echo   for /f "usebackq eol=# tokens=1,* delims==" %%%%A in ^("%%DIR%%.env"^) do if not "%%%%A"=="" if not "%%%%B"=="" set "%%%%A=%%%%B"
  echo ^)
  echo start "" "%%DIR%%bro.exe" %%*
) > "dist\bro.bat"

echo ==^> Done
dir /b dist\bro.exe dist\bro.bat
echo.
echo Run:  dist\bro.exe
echo   or: dist\bro.bat
exit /b 0
