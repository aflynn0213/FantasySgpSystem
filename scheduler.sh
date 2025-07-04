#!/bin/bash
set -e

# === CONFIGURATION ===
PROJECT_ID="fantasysgpsystem"
REGION="us-central1"
JOB_NAME="inseason-job"
SCHEDULER_NAME="inseason-scheduler"
SCHEDULE="0 7 * * *"  # 2 AM Central = 7 AM UTC
SERVICE_ACCOUNT="scheduler-invoker@fantasysgpsystem.iam.gserviceaccount.com"


# === Enable APIs ===
gcloud services enable cloudscheduler.googleapis.com

# === Create Scheduler Job ===
echo "[*] Creating Cloud Scheduler job..."
if gcloud scheduler jobs describe $SCHEDULER_NAME --location=$REGION > /dev/null 2>&1; then
  echo "[*] Scheduler exists — updating..."
  gcloud scheduler jobs update http $SCHEDULER_NAME \
    --location=$REGION \
    --schedule="$SCHEDULE" \
    --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/$JOB_NAME:run" \
    --http-method=POST \
    --oauth-service-account-email=$SERVICE_ACCOUNT \
    --oauth-token-scope="https://www.googleapis.com/auth/cloud-platform"
else
  echo "[*] Creating Cloud Scheduler job..."
  gcloud scheduler jobs create http $SCHEDULER_NAME \
    --location=$REGION \
    --schedule="$SCHEDULE" \
    --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/$JOB_NAME:run" \
    --http-method=POST \
    --oauth-service-account-email=$SERVICE_ACCOUNT \
    --oauth-token-scope="https://www.googleapis.com/auth/cloud-platform"
fi

echo "[✓] Scheduler created to run job '$JOB_NAME' nightly at 2 AM Central."