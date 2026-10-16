@echo off
title Go Green - Smart Waste Management Platform
echo ===================================================
echo   Starting Go Green Waste Management Platform...
echo ===================================================
echo.
echo Starting Flask Python server on http://127.0.0.1:5000
echo (Keep this terminal window open while using the app)
echo.

python backend/app.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Trying python from backend folder...
    cd backend
    python app.py
)
pause

