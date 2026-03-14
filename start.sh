#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "Erstelle virtuelle Umgebung..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt
echo "Starte Spielesammlung..."
python app.py
