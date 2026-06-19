#!/bin/bash

# Change directory to the location of this script
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo "Installing requirements..."
    pip install -r requirements.txt
    echo "Installing playwright browsers..."
    python -m playwright install chromium
else
    source .venv/bin/activate
fi

echo "Starting Social Media Automation Agent..."
export PORT=5005
python main.py
