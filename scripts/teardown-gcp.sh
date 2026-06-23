#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# Autonomous Analytics Agents — Teardown: remove all GCP resources
# ═══════════════════════════════════════════════════════════════
# Usage:
#   ./scripts/teardown-gcp.sh
# WARNING: This DELETES everything — Cloud Run service, GCS bucket, Artifact Registry
#          GCS bucket, Artifact Registry images.  Irreversible.
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

PROJECT_ID="${GCP_PROJECT:-$(gcloud config get project)}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="analytics-agents"
BUCKET_NAME="${PROJECT_ID}-analytics-agents-storage"

echo "⚠️  This will DELETE all Autonomous Analytics Agents resources in project '$PROJECT_ID'."
echo "    - Cloud Run service: $SERVICE_NAME"
echo "    - GCS bucket:        $BUCKET_NAME"
echo "    - Artifact Registry: analytics-agents"
read -r -p "Are you sure? Type 'yes' to continue: " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "🗑️  Deleting Cloud Run service …"
gcloud run services delete "$SERVICE_NAME" \
  --region="$REGION" \
  --project="$PROJECT_ID" \
  --quiet 2>/dev/null || echo "   (already deleted)"

echo "🗑️  Deleting GCS bucket …"
gcloud storage rm --recursive "gs://${BUCKET_NAME}" 2>/dev/null || echo "   (already deleted)"

echo "🗑️  Deleting Artifact Registry repository …"
gcloud artifacts repositories delete analytics-agents \
  --location="$REGION" \
  --project="$PROJECT_ID" \
  --quiet 2>/dev/null || echo "   (already deleted)"

echo ""
echo "✅ All Autonomous Analytics Agents resources deleted from $PROJECT_ID."
