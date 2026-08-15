@echo off
REM bro — Windows launcher (source tree or installed package)
setlocal EnableExtensions

set "ROOT=%~dp0"
cd /d "%ROOT%"

if exist "%ROOT%.venv\Scripts\python.exe" (
  set "PY=%ROOT%.venv\Scripts\python.exe"
) else (
  where py >nul 2>&1 && (
    set "PY=py -3"
  ) || (
    where python >nul 2>&1 && (
      set "PY=python"
    ) || (
      echo error: Python 3.11+ not found. Install Python or create .venv
      exit /b 1
    )
  )
)

set "PYTHONPATH=%ROOT%src;%PYTHONPATH%"

REM Load simple KEY=VALUE lines from .env (no export / quotes handling)
if exist "%ROOT%.env" (
  for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%ROOT%.env") do (
    if not "%%A"=="" if not "%%B"=="" set "%%A=%%B"
  )
)

%PY% -m bro %*
exit /b %ERRORLEVEL%
