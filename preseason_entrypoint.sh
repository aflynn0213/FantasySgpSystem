#!/bin/bash
set -e  # Exit immediately if any command fails

echo "[*] Refreshing projections..."
python update_scripts/refresh_excel_projections.py
python main.py -b atc_pre -p oopsy_pre -a atc
python main.py -b atc_pre -p oopsy_pre -a atc -m points -sb

#echo "[*] Starting Flask app..."
#exec python app.py
