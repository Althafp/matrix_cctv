#!/bin/bash
# Deployment script for Google Cloud Run

set -e  # Exit on error

echo "=========================================="
echo "🚀 CCTV Analyzer - Cloud Deployment"
echo "=========================================="

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found!"
    echo "Please install: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Configuration
PROJECT_ID="${GCS_PROJECT_ID:-focus-cumulus-477711-g5}"
REGION="us-central1"
SERVICE_NAME="cctv-analyzer"

echo ""
echo "📋 Configuration:"
echo "   Project ID: $PROJECT_ID"
echo "   Region: $REGION"
echo "   Service: $SERVICE_NAME"
echo ""

# Confirm
read -p "❓ Continue with deployment? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "❌ Deployment cancelled"
    exit 0
fi

echo ""
echo "1️⃣  Setting up project..."
gcloud config set project $PROJECT_ID

echo ""
echo "2️⃣  Enabling required APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com

echo ""
echo "3️⃣  Building container image..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

echo ""
echo "4️⃣  Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 3600 \
    --max-instances 10 \
    --set-env-vars "USE_GCS_STORAGE=true" \
    --set-env-vars "GCS_PROJECT_ID=$PROJECT_ID" \
    --set-env-vars "GCS_BUCKET_NAME=${GCS_BUCKET_NAME:-ap_cctv_test_bucket}" \
    --set-env-vars "IMAGES_DIR=${IMAGES_DIR:-test}" \
    --set-secrets "OPENAI_API_KEY=OPENAI_API_KEY:latest" \
    --set-secrets "GOOGLE_APPLICATION_CREDENTIALS=GCS_KEY:latest"

echo ""
echo "=========================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "=========================================="

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

echo ""
echo "🌐 Your app is live at:"
echo "   $SERVICE_URL"
echo ""
echo "📊 Monitor logs:"
echo "   gcloud run logs tail $SERVICE_NAME --region $REGION"
echo ""
echo "🎉 Done!"

