#!/bin/bash
set -e

# === CONFIGURATION ===
PROJECT_ID="fantasysgpsystem"
REGION="us-central1"
JOB_NAME="inseason-job"
SCHEDULER_NAME="inseason-scheduler"
SCHEDULE="0 7 * * *"  # 2 AM Central = 7 AM UTC
SERVICE_ACCOUNT="scheduler-invoker@fantasysgpsystem.iam.gserviceaccount.com"

# === The Cloud Build trigger ID for the master branch trigger ===
# Find this in Cloud Build → Triggers → click your master trigger → copy ID from the URL
TRIGGER_ID="b44036b2-8937-4162-a326-5d264748a4f7"

# === Enable APIs ===
gcloud services enable cloudscheduler.googleapis.com

# === Create Scheduler Job ===
# The scheduler triggers Cloud Build (which builds fresh master image + runs the job)
# Cloud Build cloudbuild.yaml handles: build → update job → execute job
echo "[*] Creating Cloud Scheduler job..."
if gcloud scheduler jobs describe $SCHEDULER_NAME --location=$REGION > /dev/null 2>&1; then
  echo "[*] Scheduler exists — updating..."
  gcloud scheduler jobs update http $SCHEDULER_NAME \
    --location=$REGION \
    --schedule="$SCHEDULE" \
    --uri="https://cloudbuild.googleapis.com/v1/projects/$PROJECT_ID/triggers/$TRIGGER_ID:run" \
    --message-body='{}' \
    --http-method=POST \
    --oauth-service-account-email=$SERVICE_ACCOUNT \
    --oauth-token-scope="https://www.googleapis.com/auth/cloud-platform"
else
  echo "[*] Creating Cloud Scheduler job..."
  gcloud scheduler jobs create http $SCHEDULER_NAME \
    --location=$REGION \
    --schedule="$SCHEDULE" \
    --uri="https://cloudbuild.googleapis.com/v1/projects/$PROJECT_ID/triggers/$TRIGGER_ID:run" \
    --message-body='{}' \
    --http-method=POST \
    --oauth-service-account-email=$SERVICE_ACCOUNT \
    --oauth-token-scope="https://www.googleapis.com/auth/cloud-platform"
fi

echo "[✓] Scheduler set to build master + run job '$JOB_NAME' nightly at 2 AM Central."
