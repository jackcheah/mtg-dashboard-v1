@echo off
echo ================================================
echo MTG Tournament Dashboard - Fresh Restart
echo ================================================
echo.

echo Stopping old server processes...
taskkill /F /IM python.exe 2>nul
timeout /t 3 /nobreak >nul

echo.
echo Starting fresh server...
echo.
start python tournament_dashboard.py

echo.
echo Server starting...
timeout /t 5 /nobreak >nul

echo.
echo ================================================
echo SERVER READY!
echo ================================================
echo.
echo Open your browser to: http://localhost:5000
echo.
echo IMPORTANT:
echo 1. Use Incognito/Private mode OR
echo 2. Press Ctrl+Shift+R (hard refresh)
echo.
echo Then:
echo - Load Participants
echo - Setup Tournament
echo - All rounds (1-4) will be available!
echo.
echo ================================================
pause

