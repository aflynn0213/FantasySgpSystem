#!/usr/bin/env bash
set -euo pipefail

# --- Config ---
PROJECT_ID="fantasysgpsystem"           # GCP project ID
REGION="us-central1"
LOCATION="$REGION"                      # Artifact Registry location
AR_REPO="fantasysgpsystem"              # AR repo name
IMAGE_NAME="sgp-viewer"

DATE_TAG="v_$(date +%y%m%d)"
GIT_SHA="$(git rev-parse --short HEAD || echo local)"
IMMUTABLE_TAG="${DATE_TAG}-${GIT_SHA}"

# UI (Streamlit)
UI_SERVICE="sgp-viewer"
UI_DOCKERFILE="Dockerfile"
UI_CONTEXT="ui"
UI_SA="sgp-gcs-access@$PROJECT_ID.iam.gserviceaccount.com"

if [[ -f .env ]]; then export $(grep -v '^#' .env | xargs); fi

gcloud config set project "$PROJECT_ID" >/dev/null
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com

# Ensure AR repo exists (no-op if already there)
gcloud artifacts repositories describe "$AR_REPO" --location="$LOCATION" >/dev/null 2>&1 || \
gcloud artifacts repositories create "$AR_REPO" --repository-format=docker --location="$LOCATION" --description="Images for FantasySgpSystem"

# Docker auth for Artifact Registry
gcloud auth configure-docker "${LOCATION}-docker.pkg.dev" --quiet

IMAGE_BASE="${LOCATION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/${IMAGE_NAME}"

echo "[*] Building UI image:  ${IMAGE_BASE}:${IMMUTABLE_TAG} (and ${DATE_TAG})"
docker build -f "$UI_DOCKERFILE" -t "${IMAGE_BASE}:${IMMUTABLE_TAG}" -t "${IMAGE_BASE}:${DATE_TAG}" "$UI_CONTEXT"
docker push "${IMAGE_BASE}:${IMMUTABLE_TAG}"
docker push "${IMAGE_BASE}:${DATE_TAG}"

echo "[*] Deploying UI service: $UI_SERVICE"
gcloud run deploy "$UI_SERVICE" \
  --image "${IMAGE_BASE}:${IMMUTABLE_TAG}" \
  --region "$REGION" \
  --allow-unauthenticated \
  --service-account "$UI_SA" \
  --memory 1Gi --min-instances 0 --max-instances 3
echo "[✓] UI ready: $UI_SERVICE"

# Get & show the URL
UI_URL="$(gcloud run services describe "$UI_SERVICE" \
  --region "$REGION" \
  --format='value(status.url)')"
echo "[✓] UI URL: $UI_URL"


# auto-open
if command -v xdg-open >/dev/null; then xdg-open "$UI_URL" >/dev/null 2>&1 || true; fi
case "$OSTYPE" in
  msys*|cygwin*) cmd.exe /c start "$UI_URL" >/dev/null 2>&1 || true ;;
  darwin*)       open "$UI_URL" >/dev/null 2>&1 || true ;;
esac
