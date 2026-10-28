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

RUN_MODE=$(OPENING_DAY="$OPENING_DAY_VALUE" python - <<'PY'
import os
from datetime import date

opening_day = date.fromisoformat(os.environ["OPENING_DAY"])
today = date.today()
print("inseason" if today >= opening_day else "preseason")
PY
)

echo "Opening day: ${OPENING_DAY_VALUE}"
echo "Selected run mode: ${RUN_MODE}"

if [ "$RUN_MODE" = "inseason" ]; then
    exec ./inseason_entrypoint.sh
fi

exec ./preseason_entrypoint.sh