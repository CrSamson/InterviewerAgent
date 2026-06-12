@echo off
setlocal

set "ROOT=%~dp0"
chcp 65001 >nul
set "PYTHONUTF8=1"
"%ROOT%.venv\Scripts\python.exe" -m interviewer_agent run %*
