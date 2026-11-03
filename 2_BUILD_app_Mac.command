#!/bin/bash
cd "$(dirname "$0")"
python3 -m pip install --quiet --no-warn-script-location pyinstaller pillow
python3 -m PyInstaller --noconfirm --onefile --windowed --name Capri --add-data "pet:pet" capri.py
echo "Done. App is in dist/"
