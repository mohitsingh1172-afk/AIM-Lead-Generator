@echo off
setlocal

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8765" ^| findstr "LISTENING"') do (
  taskkill /PID %%a /F
)

echo AIM Lead Generator stopped if it was running on port 8765.
