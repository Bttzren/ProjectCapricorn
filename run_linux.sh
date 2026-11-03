#!/bin/bash
cd "$(dirname "$0")"
python3 -m pip install --quiet --break-system-packages pillow
python3 capri.py
