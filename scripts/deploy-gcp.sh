#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# Autonomous Analytics Agents — One-Command GCP Deployment
# ═══════════════════════════════════════════════════════════════
#
# Usage:
#   ./scripts/deploy-gcp.sh
#
# Prerequisites:
#   1. Install gcloud CLI: https://cloud.google.com/sdk/docs/install
#   2. gcloud auth login
#   3. gcloud config set project YOUR_PROJECT_ID
#
# This script:
#   • Enables required GCP APIs
#   • Creates Artifact Registry repository
#   • Creates GCS bucket for file storage
#   • Builds & pushes Docker image
#   • Deploys to Cloud Run with API keys as environment variables
#   • Prints the service URL
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

# ── Configuration ──────────────────────────────────────────────
PROJECT_ID="${GCP_PROJECT:-$(gcloud config get project)}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="analytics-agents"
BUCKET_NAME="${PROJECT_ID}-analytics-agents-storage"
ARTIFACT_REPO="analytics-agents"

echo "🚀 Autonomous Analytics Agents — GCP Deployment"
echo "   Project:  $PROJECT_ID"
echo "   Region:   $REGION"
echo "   Service:  $SERVICE_NAME"
echo ""

# ── Step 1: Enable APIs ───────────────────────────────────────
echo "📡 [1/7] Enabling GCP APIs …"
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com \
  --project="$PROJECT_ID" 2>/dev/null || true

# ── Step 2: Create Artifact Registry ──────────────────────────
echo "📦 [2/7] Creating Artifact Registry …"
gcloud artifacts repositories create "$ARTIFACT_REPO" \
  --repository-format=docker \
  --location="$REGION" \
  --project="$PROJECT_ID" 2>/dev/null || echo "   (already exists)"

# ── Step 3: Create GCS bucket ─────────────────────────────────
echo "🪣 [3/7] Creating Cloud Storage bucket …"
gcloud storage buckets create "gs://${BUCKET_NAME}" \
  --location="$REGION" \
  --project="$PROJECT_ID" 2>/dev/null || echo "   (already exists)"

# ── Step 4: Prepare API keys ──────────────────────────────────
echo "🔐 [4/7] Preparing API keys for deployment …"
declare -A ENV_VARS=(
  ["OPENAI_API_KEY"]="${OPENAI_API_KEY:-}"
  ["ANTHROPIC_API_KEY"]="${ANTHROPIC_API_KEY:-}"
  ["GROQ_API_KEY"]="${GROQ_API_KEY:-}"
  ["TOGETHER_API_KEY"]="${TOGETHER_API_KEY:-}"
  ["GOOGLE_API_KEY"]="${GOOGLE_API_KEY:-}"
)

for KEY_NAME in "${!ENV_VARS[@]}"; do
  VALUE="${ENV_VARS[$KEY_NAME]}"
  if [ -n "$VALUE" ]; then
    echo "   ✅ $KEY_NAME (will be passed as env var)"
  else
    echo "   ⚠️  $KEY_NAME not set — skipping"
  fi
done

# ── Step 5: Build Docker image ────────────────────────────────
echo "🐳 [5/7] Building Docker image …"
IMAGE="us-central1-docker.pkg.dev/$PROJECT_ID/$ARTIFACT_REPO/$SERVICE_NAME"

docker build -t "$IMAGE:latest" .

# ── Step 6: Push to Artifact Registry ─────────────────────────
echo "📤 [6/7] Pushing to Artifact Registry …"
docker push "$IMAGE:latest"

# ── Step 7: Deploy to Cloud Run ───────────────────────────────
echo "☁️  [7/7] Deploying to Cloud Run …"

# Build environment variables string with optional API keys
ENV_VARS="GCP_PROJECT=$PROJECT_ID,GCS_BUCKET_NAME=$BUCKET_NAME,LLM_PROVIDER=openai"

# Add API keys if provided
if [ -n "${OPENAI_API_KEY:-}" ]; then
  ENV_VARS="$ENV_VARS,OPENAI_API_KEY=$OPENAI_API_KEY"
fi
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  ENV_VARS="$ENV_VARS,ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY"
fi
if [ -n "${GROQ_API_KEY:-}" ]; then
  ENV_VARS="$ENV_VARS,GROQ_API_KEY=$GROQ_API_KEY"
fi
if [ -n "${TOGETHER_API_KEY:-}" ]; then
  ENV_VARS="$ENV_VARS,TOGETHER_API_KEY=$TOGETHER_API_KEY"
fi
if [ -n "${GOOGLE_API_KEY:-}" ]; then
  ENV_VARS="$ENV_VARS,GOOGLE_API_KEY=$GOOGLE_API_KEY"
fi

gcloud run deploy "$SERVICE_NAME" \
  --image="$IMAGE:latest" \
  --region="$REGION" \
  --platform=managed \
  --allow-unauthenticated \
  --memory=4Gi \
  --cpu=2 \
  --timeout=900 \
  --max-instances=5 \
  --concurrency=10 \
  --set-env-vars="$ENV_VARS" \
  --clear-secrets \
  --project="$PROJECT_ID"

# ── Done ───────────────────────────────────────────────────────
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --region="$REGION" \
  --format="value(status.url)" \
  --project="$PROJECT_ID")

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ Deployment complete!"
echo "   🌐 URL: $SERVICE_URL"
echo ""
echo "   Monitor:  https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME"
echo "   Logs:     gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME' --limit=20"
echo "═══════════════════════════════════════════════════════════"
