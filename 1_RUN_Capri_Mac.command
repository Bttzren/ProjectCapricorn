#!/bin/bash
cd "$(dirname "$0")"
python3 -m pip install --quiet --no-warn-script-location pillow
python3 capri.py
