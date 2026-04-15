@echo off
cd /d %~dp0
py scripts\entrypoint.py --gui
if %errorlevel% neq 0 python scripts\entrypoint.py --gui
pause
