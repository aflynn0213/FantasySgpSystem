#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="fantasysgpsystem"
REGION="us-central1"
DATE_TAG="v_$(date +%y%m%d)"

# UI (Streamlit)
UI_SERVICE="sgp-viewer"
UI_IMAGE="gcr.io/$PROJECT_ID/sgp-viewer:$DATE_TAG"
UI_DOCKERFILE="ui/Dockerfile"
UI_CONTEXT="ui"
UI_SA="sgp-gcs-access@$PROJECT_ID.iam.gserviceaccount.com"    # read-only perms on bucket

if [[ -f .env ]]; then export $(grep -v '^#' .env | xargs); fi

gcloud config set project "$PROJECT_ID" >/dev/null
gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com

gcloud auth configure-docker --quiet

echo "[*] Building UI image:  $UI_IMAGE"
docker build -f "$UI_DOCKERFILE" -t "$UI_IMAGE" "$UI_CONTEXT"
docker push "$UI_IMAGE"

echo "[*] Deploying UI service: $UI_SERVICE"
gcloud run deploy "$UI_SERVICE" \
  --image "$UI_IMAGE" \
  --region "$REGION" \
  --allow-unauthenticated \
  --service-account "$UI_SA" \
  --memory 1Gi --min-instances 0 --max-instances 3
echo "[✓] UI ready: $UI_SERVICE"

# ===== Get & show the URL =====
UI_URL="$(gcloud run services describe "$UI_SERVICE" \
  --region "$REGION" \
  --format='value(status.url)')"

echo "[✓] UI URL: $UI_URL"

# Optional: copy to clipboard
case "$OSTYPE" in
  msys*|cygwin*)  # Git Bash on Windows
    echo -n "$UI_URL" | clip.exe ;;
  darwin*)        # macOS
    echo -n "$UI_URL" | pbcopy ;;
  linux*)         # Linux with xclip
    command -v xclip >/dev/null && echo -n "$UI_URL" | xclip -selection clipboard || true ;;
esac

# Optional: auto-open (Windows/macOS; Linux if xdg-open exists)
if command -v xdg-open >/dev/null; then xdg-open "$UI_URL" >/dev/null 2>&1 || true; fi
case "$OSTYPE" in
  msys*|cygwin*) cmd.exe /c start "$UI_URL" >/dev/null 2>&1 || true ;;
  darwin*)       open "$UI_URL" >/dev/null 2>&1 || true ;;
esac
