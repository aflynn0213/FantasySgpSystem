#!/usr/bin/env bash
set -euo pipefail

# --- Config ---
PROJECT_ID="fantasysgpsystem"
REGION="us-central1"
DATE_TAG="v_$(date +%y%m%d)"

# Job (batch)
JOB_NAME="inseason-job"
JOB_IMAGE="gcr.io/$PROJECT_ID/inseason-sgp:$DATE_TAG"
JOB_DOCKERFILE="Dockerfile.job"
JOB_CONTEXT="."
JOB_SA="sgp-gcs-access@$PROJECT_ID.iam.gserviceaccount.com"   # runtime SA for the job


# Optional: load .env
if [[ -f .env ]]; then export $(grep -v '^#' .env | xargs); fi

gcloud config set project "$PROJECT_ID" >/dev/null
gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com

# Ensure Docker can push to gcr.io (one-time per machine)
gcloud auth configure-docker --quiet

echo "[*] Building JOB image: $JOB_IMAGE"
docker build -f "$JOB_DOCKERFILE" -t "$JOB_IMAGE" "$JOB_CONTEXT"
docker push "$JOB_IMAGE"

echo "[*] Deploying/Updating Cloud Run JOB: $JOB_NAME"
if gcloud run jobs describe "$JOB_NAME" --region "$REGION" >/dev/null 2>&1; then
  gcloud run jobs update "$JOB_NAME" \
    --image "$JOB_IMAGE" \
    --region "$REGION" \
    --memory 1Gi \
    --service-account "$JOB_SA" \
    --set-secrets=FANGRAPHS_USERNAME=fangraphs-username:latest,FANGRAPHS_PASSWORD=fangraphs-password:latest
else
  gcloud run jobs create "$JOB_NAME" \
    --image "$JOB_IMAGE" \
    --region "$REGION" \
    --memory 1Gi \
    --service-account "$JOB_SA" \
    --set-secrets=FANGRAPHS_USERNAME=fangraphs-username:latest,FANGRAPHS_PASSWORD=fangraphs-password:latest
fi
echo "[✓] Job ready: $JOB_NAME"


