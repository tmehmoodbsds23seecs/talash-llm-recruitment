@echo off
echo Starting TALASH Backend Server...
cd /d "%~dp0"
call ..\backend\venv\Scripts\python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000