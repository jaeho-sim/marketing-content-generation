#!/usr/bin/env bash
# One-time GCP resource bootstrap.
# Usage: PROJECT_ID=your-project REGION=us-central1 ./infra/setup_gcp.sh
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID}"
REGION="${REGION:-us-central1}"
BUCKET="${BUCKET:-marketing-content-media}"
TOPIC="${TOPIC:-media-uploaded}"
BACKEND_URL="${BACKEND_URL:-}"   # Set after first Cloud Run deploy

gcloud config set project "$PROJECT_ID"

echo "==> Enabling APIs"
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  storage.googleapis.com \
  pubsub.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com

echo "==> GCS bucket"
gcloud storage buckets create "gs://$BUCKET" \
  --project="$PROJECT_ID" \
  --location="$REGION" \
  --uniform-bucket-level-access || true

echo "==> Pub/Sub topic"
gcloud pubsub topics create "$TOPIC" --project="$PROJECT_ID" || true

echo "==> GCS → Pub/Sub notification"
gcloud storage buckets notifications create "gs://$BUCKET" \
  --topic="$TOPIC" \
  --event-types=OBJECT_FINALIZE \
  --payload-format=JSON_API_V1

echo "==> Service account"
SA_NAME="marketing-content-sa"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"
gcloud iam service-accounts create "$SA_NAME" \
  --display-name="Marketing Content Generation App" || true

for ROLE in \
  roles/storage.objectAdmin \
  roles/pubsub.subscriber \
  roles/cloudsql.client \
  roles/secretmanager.secretAccessor \
  roles/iam.serviceAccountTokenCreator; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="$ROLE"
done

echo "==> Artifact Registry"
gcloud artifacts repositories create marketing-content \
  --repository-format=docker \
  --location="$REGION" || true

echo ""
echo "Next — Cloud SQL:"
echo "  gcloud sql instances create marketing-content-db \\"
echo "    --database-version=POSTGRES_16 --tier=db-f1-micro \\"
echo "    --region=$REGION"
echo "  gcloud sql databases create marketing_content --instance=marketing-content-db"
echo "  gcloud sql users create app --instance=marketing-content-db --password=<password>"
echo ""

if [[ -n "$BACKEND_URL" ]]; then
  TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
  echo "==> Pub/Sub push subscription (token: $TOKEN)"
  gcloud pubsub subscriptions create media-uploaded-sub \
    --topic="$TOPIC" \
    --push-endpoint="$BACKEND_URL/webhooks/gcs?token=$TOKEN" \
    --ack-deadline=300
  echo "Store this token in Secret Manager as 'pubsub-webhook-token'"
else
  echo "Set BACKEND_URL=<cloud-run-url> and re-run to create the Pub/Sub subscription."
fi

echo "Done."
