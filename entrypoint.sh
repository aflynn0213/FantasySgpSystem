#!/bin/bash
set -e  # Exit immediately if any command fails

echo "[*] Refreshing projections..."
python refresh_excel_projections.py

echo "[*] Starting Flask app..."
exec python app.py
