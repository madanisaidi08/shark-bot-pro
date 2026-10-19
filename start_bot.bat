@echo off
title Binance Spot & TradingView Bot
cd /d "%~dp0"
echo Starting Binance TradingView Bot...
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe run.py
) else (
    python run.py
)
pause
