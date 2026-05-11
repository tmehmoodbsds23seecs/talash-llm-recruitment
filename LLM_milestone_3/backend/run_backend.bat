@echo off
cd /d "%~dp0"
echo Starting TALASH Backend...
call venv\Scripts\activate.bat
python main.py