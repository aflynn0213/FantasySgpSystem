#!/bin/bash
set -e

echo "Running in-season job..."
python update_scripts/update_stats.py
python main.py -b atc_td -p atc_td -wk $(python -c "from datetime import datetime; print(min(26, (datetime.today() - datetime(2025, 3, 24)).days // 7))")
#python main.py -b batx_ros -p oopsy_ros -wk $(python -c "from datetime import datetime; print(min(26, (datetime.today() - datetime(2025, 3, 24)).days // 7))")