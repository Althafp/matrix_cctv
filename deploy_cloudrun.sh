#!/bin/bash
# Quick Deploy to Google Cloud Run
# One-command deployment script

set -e

echo "=========================================="
echo "🚀 Deploying to Google Cloud Run"
echo "=========================================="
echo ""

# Configuration
PROJECT_ID="focus-cumulus-477711-g5"
REGION="us-central1"
SERVICE_NAME="cctv-analyzer"

echo "📋 Configuration:"
echo "   Project: $PROJECT_ID"
echo "   Region: $REGION"
echo "   Service: $SERVICE_NAME"
echo ""

# Set project
echo "⚙️  Setting project..."
gcloud config set project $PROJECT_ID

# Enable APIs
echo "🔧 Enabling required APIs..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

# Deploy
echo ""
echo "🚀 Deploying to Cloud Run..."
echo ""

gcloud run deploy $SERVICE_NAME \
  --source . \
  --region $REGION \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --max-instances 10 \
  --set-env-vars "USE_GCS_STORAGE=true,GCS_PROJECT_ID=$PROJECT_ID,GCS_BUCKET_NAME=ap_cctv_test_bucket,IMAGES_DIR=test,MAX_WORKERS=5"

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format='value(status.url)')

echo ""
echo "=========================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "🌐 Your app is live at:"
echo "   $SERVICE_URL"
echo ""
echo "📊 View in console:"
echo "   https://console.cloud.google.com/run?project=$PROJECT_ID"
echo ""
echo "📝 View logs:"
echo "   gcloud run logs tail $SERVICE_NAME --region $REGION"
echo ""
echo "🎉 Done!"

