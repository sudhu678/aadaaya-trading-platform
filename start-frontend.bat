@echo off
cd /d "%~dp0dashboard\ui"
if not exist "node_modules" ( call npm install || exit /b 1 )
call npm run dev
