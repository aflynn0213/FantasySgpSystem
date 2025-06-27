#!/bin/bash
set -e

echo "[*] Running in-season job..."
python update_stats.py
python in_season_sgp.py -b atc_td -wk $(python -c "from datetime import datetime; print((datetime.today() - datetime(2025, 3, 24)).days // 7)")
python in_season_sgp.py -b batx_ros -wk $(python -c "from datetime import datetime; print((datetime.today() - datetime(2025, 3, 24)).days // 7)")
