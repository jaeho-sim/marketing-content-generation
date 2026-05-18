#!/usr/bin/env bash
# Build and deploy backend + frontend to Cloud Run.
# Run from repo root.
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID}"
REGION="${REGION:-us-central1}"
REGISTRY="$REGION-docker.pkg.dev/$PROJECT_ID/marketing-content"
SQL_INSTANCE="$PROJECT_ID:$REGION:marketing-content-db"

gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet

# ── Backend ────────────────────────────────────────────────────────────────
BACKEND_IMAGE="$REGISTRY/backend"
echo "==> Building backend"
docker build -t "$BACKEND_IMAGE:latest" ./backend
docker push "$BACKEND_IMAGE:latest"

echo "==> Deploying backend to Cloud Run"
gcloud run deploy marketing-content-backend \
  --image="$BACKEND_IMAGE:latest" \
  --region="$REGION" \
  --platform=managed \
  --service-account="marketing-content-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --set-secrets="ANTHROPIC_API_KEY=anthropic-api-key:latest,PUBSUB_WEBHOOK_TOKEN=pubsub-webhook-token:latest,SECRET_KEY=app-secret-key:latest" \
  --set-env-vars="APP_ENV=production,GCS_PROJECT_ID=$PROJECT_ID,GCS_BUCKET_NAME=marketing-content-media,PUBSUB_TOPIC=media-uploaded" \
  --add-cloudsql-instances="$SQL_INSTANCE" \
  --set-env-vars="DATABASE_URL=postgresql+asyncpg:///marketing_content?host=/cloudsql/$SQL_INSTANCE&user=app&password=\${DB_PASSWORD}" \
  --allow-unauthenticated \
  --min-instances=1 \
  --max-instances=10 \
  --memory=2Gi \
  --cpu=2

BACKEND_URL=$(gcloud run services describe marketing-content-backend \
  --region="$REGION" --format="value(status.url)")
echo "Backend: $BACKEND_URL"

# ── Frontend ───────────────────────────────────────────────────────────────
FRONTEND_IMAGE="$REGISTRY/frontend"
echo "==> Building frontend"
docker build \
  --target prod \
  --build-arg VITE_API_BASE_URL="$BACKEND_URL" \
  -t "$FRONTEND_IMAGE:latest" ./frontend
docker push "$FRONTEND_IMAGE:latest"

echo "==> Deploying frontend to Cloud Run"
gcloud run deploy marketing-content-frontend \
  --image="$FRONTEND_IMAGE:latest" \
  --region="$REGION" \
  --platform=managed \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=5 \
  --memory=256Mi

FRONTEND_URL=$(gcloud run services describe marketing-content-frontend \
  --region="$REGION" --format="value(status.url)")
echo "Frontend: $FRONTEND_URL"
echo "Done."
