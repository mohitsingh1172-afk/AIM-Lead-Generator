@echo off
setlocal

set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT=%STARTUP_DIR%\AIM Lead Generator.lnk"
set "TARGET=%~dp0run_web_app_hidden.vbs"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%SHORTCUT%'); $s.TargetPath='%TARGET%'; $s.WorkingDirectory='%~dp0'; $s.Save()"

echo AIM Lead Generator will now start automatically when Windows starts.
echo Website: http://127.0.0.1:8765
