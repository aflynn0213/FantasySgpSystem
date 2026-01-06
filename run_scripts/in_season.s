#!/bin/bash

#python update_scripts/update_stats.py
#python ../main.py -b atc_td -p atc_td -wk $(python -c "from datetime import datetime; print((datetime.today() - datetime(2025, 3, 24)).days // 7)")
#python ../main.py -b batx_ros -p oopsy_ros -wk $(python -c "from datetime import datetime; print((datetime.today() - datetime(2025, 3, 24)).days // 7)")
python main.py -b _eoy -p _eoy -wk 26


