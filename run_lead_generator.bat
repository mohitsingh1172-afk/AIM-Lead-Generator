@echo off
setlocal

set "BUNDLED_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if exist "%BUNDLED_PYTHON%" (
  "%BUNDLED_PYTHON%" "%~dp0lead_generator.py" %*
) else (
  py "%~dp0lead_generator.py" %*
)
