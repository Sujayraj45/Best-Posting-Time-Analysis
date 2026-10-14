@echo off
title Best Posting Time Analysis - Python
echo ========================================================
echo   Best Posting Time Analysis (Flask Server)
echo ========================================================
echo.
echo Installing dependencies if needed...
py -m pip install -r requirements.txt --quiet
echo.
echo Starting Flask application at http://localhost:5000 ...
echo.
start http://localhost:5000
py app.py
pause
