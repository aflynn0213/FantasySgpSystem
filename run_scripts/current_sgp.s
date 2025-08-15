#!/bin/bash

python update_stats.py
python in_season_main.py -b atc_td -wk $(python -c "from datetime import datetime; print((datetime.today() - datetime(2025, 3, 24)).days // 7)")
python in_season_main.py -b batx_ros -wk $(python -c "from datetime import datetime; print((datetime.today() - datetime(2025, 3, 24)).days // 7)")
