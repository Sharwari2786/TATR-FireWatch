@echo off
cd /d "%~dp0"

if not exist ".venv" (
  python -m venv .venv
)

call .venv\Scripts\activate.bat
pip install -q -r requirements.txt

cd backend
if not exist "data\raw" mkdir data\raw
if not exist "data\processed" mkdir data\processed
if not exist "model" mkdir model

python pipeline.py
python app.py
