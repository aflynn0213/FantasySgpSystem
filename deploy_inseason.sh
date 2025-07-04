#!/bin/bash
set -e  # Exit on error

export $(grep -v '^#' .env | xargs)

# === CONFIGURATION ===
PROJECT_ID="fantasysgpsystem"
IMAGE_NAME="inseason-sgp"
REGION="us-central1"
SERVICE_NAME="inseason-job"
SERVICE_ACCOUNT="scheduler-invoker@$PROJECT_ID.iam.gserviceaccount.com"

DATE_TAG="v_$(date +%y%m%d)"   # e.g., v_250626
FULL_IMAGE="gcr.io/$PROJECT_ID/$IMAGE_NAME:$DATE_TAG"

gcloud services enable secretmanager.googleapis.com

# === 1. Build Docker image ===
echo "[*] Building Docker image with tag: $DATE_TAG..."
docker build -t $FULL_IMAGE .

# === 2. Push to Google Container Registry ===
echo "[*] Pushing Docker image to GCR..."
docker push $FULL_IMAGE

# === 3. Deploy to Cloud Run ===
echo "[*] Deploying to Cloud Run as $SERVICE_NAME..."
echo "[*] Checking if job exists..."
if gcloud run jobs describe "$SERVICE_NAME" --region="$REGION" >/dev/null 2>&1; then
  echo "[*] Job exists — updating..."
  gcloud run jobs update "$SERVICE_NAME" \
    --image "$FULL_IMAGE" \
    --region "$REGION" \
    --memory 1Gi \
    --service-account "$SERVICE_ACCOUNT" \
    --set-secrets=FANGRAPHS_USERNAME=fangraphs-username:latest,FANGRAPHS_PASSWORD=fangraphs-password:latest
else
  echo "[*] Job does not exist — creating..."
  gcloud run jobs create "$SERVICE_NAME" \
    --image "$FULL_IMAGE" \
    --region "$REGION" \
    --memory 1Gi \
    --service-account "$SERVICE_ACCOUNT" \
    --set-secrets=FANGRAPHS_USERNAME=fangraphs-username:latest,FANGRAPHS_PASSWORD=fangraphs-password:latest
fi

echo "[✓] Deployed in-season job successfully."
