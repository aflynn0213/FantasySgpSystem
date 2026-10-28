#!/bin/bash
set -e

OPENING_DAY_VALUE=$(python - <<'PY'
import os
from pathlib import Path

opening_day = os.environ.get("OPENING_DAY")
if opening_day:
	print(opening_day)
	raise SystemExit

config_path = Path("/FantasySgpSystem/config.yml")
if config_path.exists():
	import yaml

	config = yaml.safe_load(config_path.read_text()) or {}
	season = config.get("season", {}) or {}
	opening_day = season.get("opening_day")

if opening_day:
	print(opening_day)
else:
	print("2025-03-24")
PY
)

CURRENT_WEEK=$(OPENING_DAY="$OPENING_DAY_VALUE" python - <<'PY'
import os
from datetime import date

opening_day = date.fromisoformat(os.environ["OPENING_DAY"])
today = date.today()
weeks = max(0, min(26, (today - opening_day).days // 7))
print(weeks)
PY
)

echo "Running in-season job..."
echo "Opening day: ${OPENING_DAY_VALUE}"
echo "Calculated week: ${CURRENT_WEEK}"
#python update_scripts/update_stats.py
python main.py -b atc_td -p atc_td -wk ${CURRENT_WEEK}
python main.py -b batx_ros -p oopsy_ros -wk ${CURRENT_WEEK}