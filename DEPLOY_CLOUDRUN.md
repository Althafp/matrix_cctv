# 🚀 Deploy to Google Cloud Run (EASIEST for you!)

Since you already have GCP set up with GCS, deploying to Cloud Run is the **EASIEST** option!

---

## ⚡ **One Command Deployment**

```bash
gcloud run deploy cctv-analyzer --source . --region us-central1 --allow-unauthenticated
```

**That's it!** ✅

---

## 📋 **Step-by-Step**

### **Step 1: Install Google Cloud SDK** (if not installed)

**Download:** https://cloud.google.com/sdk/docs/install

**Or quick install:**
```bash
# Windows: Download installer from above link
# Linux:
curl https://sdk.cloud.google.com | bash

# Mac:
brew install --cask google-cloud-sdk
```

### **Step 2: Login and Setup**

```bash
# Login to your Google account
gcloud auth login

# Set your project
gcloud config set project focus-cumulus-477711-g5

# Enable required APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com
```

### **Step 3: Deploy (ONE COMMAND!)**

```bash
# Navigate to your project
cd "D:\chandu sir\flask"

# Deploy!
gcloud run deploy cctv-analyzer \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --max-instances 10
```

**Answer the prompts:**
- Service name: `cctv-analyzer` (press Enter)
- Region: `us-central1` (or choose closest to you)
- Allow unauthenticated: `y`

**Wait 3-5 minutes...**

**Done!** You'll get a URL like:
```
https://cctv-analyzer-abc123-uc.a.run.app
```

---

## 🔐 **Set Environment Variables**

After first deployment, add your secrets:

```bash
# Add OpenAI API Key as secret
echo "your_openai_key" | gcloud secrets create OPENAI_API_KEY --data-file=-

# Update service to use secrets
gcloud run services update cctv-analyzer \
  --region us-central1 \
  --set-env-vars "USE_GCS_STORAGE=true" \
  --set-env-vars "GCS_PROJECT_ID=focus-cumulus-477711-g5" \
  --set-env-vars "GCS_BUCKET_NAME=ap_cctv_test_bucket" \
  --set-env-vars "IMAGES_DIR=test" \
  --set-env-vars "MAX_WORKERS=5" \
  --update-secrets "OPENAI_API_KEY=OPENAI_API_KEY:latest"
```

**Or add via Web UI:**
1. Go to: https://console.cloud.google.com/run
2. Click your service: `cctv-analyzer`
3. Click **"Edit & Deploy New Revision"**
4. Add environment variables
5. Save

---

## 🎯 **Why Cloud Run is EASIEST for You**

✅ **Already have GCP** - Same project as GCS  
✅ **One command** - `gcloud run deploy`  
✅ **Same ecosystem** - Integrates perfectly with GCS  
✅ **No config needed** - Auto-detects Python/Flask  
✅ **Service account** - Already has GCS access!  
✅ **Zero storage** - Works with direct URLs perfectly  

---

## 💰 **Cost (Very Affordable)**

**Cloud Run Pricing:**
```
First 2 million requests/month: FREE
First 360,000 GB-seconds/month: FREE

Your usage (estimated):
- Requests: ~10,000/month
- Cost: $0-2/month (within free tier!)

Plus GCS: $2/month
Total: $2-4/month ✅
```

---

## 📊 **Comparison**

| Platform | Setup | Cost | Integration |
|----------|-------|------|-------------|
| **Cloud Run** | ⭐⭐⭐⭐⭐ | $0-2/mo | Perfect (same GCP) ✅ |
| Render.com | ⭐⭐⭐⭐ | $0/mo | Good |
| Railway | ⭐⭐⭐ | $5 credit | Good |

**Cloud Run = Best for your setup!** ✅

---

## 🚀 **Quick Deploy Script**

I'll create a simple script for you:

```bash
#!/bin/bash
# Quick deploy to Cloud Run

gcloud run deploy cctv-analyzer \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --set-env-vars "USE_GCS_STORAGE=true,GCS_PROJECT_ID=focus-cumulus-477711-g5,GCS_BUCKET_NAME=ap_cctv_test_bucket,IMAGES_DIR=test,MAX_WORKERS=5"

echo "✅ Deployed! Check URL above"
```

Save as `deploy_cloudrun.sh` and run:
```bash
chmod +x deploy_cloudrun.sh
./deploy_cloudrun.sh
```

---

## ⚡ **Super Quick Deploy (Copy-Paste)**

```bash
# Login (one time)
gcloud auth login
gcloud config set project focus-cumulus-477711-g5

# Deploy (every time)
gcloud run deploy cctv-analyzer --source . --region us-central1 --allow-unauthenticated
```

**Done in 5 minutes!** ✅

---

## 🔍 **Monitor Your App**

```bash
# View logs
gcloud run logs tail cctv-analyzer --region us-central1

# Get service URL
gcloud run services describe cctv-analyzer --region us-central1 --format='value(status.url)'

# View in console
https://console.cloud.google.com/run?project=focus-cumulus-477711-g5
```

---

## ✅ **Advantages for You**

Since you already have:
- ✅ GCP project setup
- ✅ GCS bucket configured
- ✅ Service account with permissions
- ✅ Same project (focus-cumulus-477711-g5)

**Cloud Run is the EASIEST because:**
- ✅ No separate service account needed (uses existing!)
- ✅ Already has GCS access
- ✅ Same billing account
- ✅ One command deployment
- ✅ Perfect integration

---

## 🎉 **Summary**

**EASIEST for your setup:**
```bash
gcloud run deploy cctv-analyzer --source . --region us-central1 --allow-unauthenticated
```

**Time:** 5 minutes  
**Cost:** $0-2/month (mostly free tier)  
**Storage:** 0 MB (direct URLs)  
**Integration:** Perfect (same GCP project)  

**Just run the command and you're live!** 🚀

---

## 📞 **Need Help?**

```bash
# Check if gcloud is installed
gcloud --version

# Install if needed
# https://cloud.google.com/sdk/docs/install

# Deploy
gcloud run deploy cctv-analyzer --source . --region us-central1 --allow-unauthenticated
```

**Easiest deployment method for your setup!** ✨

