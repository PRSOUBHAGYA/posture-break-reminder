#!/bin/bash

# Exit on error
set -e

echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Verifying installations..."
python3 -c "import cv2; print('opencv-python: OK')"
python3 -c "import mediapipe; print('mediapipe: OK')"
python3 -c "import rumps; print('rumps: OK')"

echo "Setup completed successfully!"
