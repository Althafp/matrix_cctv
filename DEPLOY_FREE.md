# 🆓 FREE Deployment Guide (No GCP!)

Complete guide to deploy your CCTV Analyzer to **FREE platforms** without Google Cloud Platform costs.

---

## ⚠️ **Why NOT Vercel?**

**Vercel has timeout limits:**
- Free tier: 10 seconds
- Pro tier: 60 seconds

**Your app needs:**
- AI image analysis: 2-5 seconds per image
- Multiple images: Can take minutes
- **Result: Vercel will timeout ❌**

---

## ⭐ **BEST FREE ALTERNATIVES**

### **Comparison:**

| Platform | Free Tier | Timeout | Flask Support | Best For |
|----------|-----------|---------|---------------|----------|
| **Render.com** | 750 hrs/mo | None ✅ | Excellent ✅ | **RECOMMENDED** |
| **Railway.app** | $5 credit/mo | None ✅ | Excellent ✅ | Great |
| **Fly.io** | 3 VMs | None ✅ | Good ✅ | Good |
| **Vercel** | Unlimited | 10-60s ❌ | Limited ⚠️ | Not ideal |

---

## 🚀 **Option 1: Render.com (RECOMMENDED)**

### **Why Render?**
- ✅ **750 hours/month FREE** (enough for 24/7)
- ✅ **No timeout limits**
- ✅ Perfect for Flask + Python
- ✅ Easy deployment (connects to GitHub)
- ✅ Still uses GCS for images (no storage issues!)

### **Deployment Steps:**

#### **Step 1: Prepare Repository**

```bash
# Make sure you have these files:
# - render.yaml (already created ✅)
# - requirements.txt (already exists ✅)
# - flask_app.py (already exists ✅)

# Commit everything
git add .
git commit -m "Ready for Render deployment"
git push origin main
```

#### **Step 2: Deploy to Render**

1. **Go to:** https://render.com
2. **Sign up** (free account)
3. **Click:** "New +" → "Web Service"
4. **Connect GitHub** repository
5. **Settings:**
   - **Name:** `cctv-analyzer`
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn flask_app:app --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0`
   - **Plan:** FREE

#### **Step 3: Add Environment Variables**

In Render dashboard, add:

```
USE_GCS_STORAGE=true
GCS_PROJECT_ID=focus-cumulus-477711-g5
GCS_BUCKET_NAME=ap_cctv_test_bucket
IMAGES_DIR=test
MAX_WORKERS=5
```

#### **Step 4: Add Secrets**

**Secret Environment Variables:**

1. **OPENAI_API_KEY:**
   - Click "Add Environment Variable"
   - Key: `OPENAI_API_KEY`
   - Value: `your_openai_api_key`

2. **GCS Credentials:**
   - Upload `gcs-key.json` as **Secret File**
   - Key: `GOOGLE_APPLICATION_CREDENTIALS`
   - Value: Upload file

#### **Step 5: Deploy**

Click **"Create Web Service"** → Automatic deployment!

**Your URL:**
```
https://cctv-analyzer.onrender.com
```

**Done!** ✅

---

## 🚂 **Option 2: Railway.app**

### **Why Railway?**
- ✅ **$5 free credit/month** (~500 hours)
- ✅ Very simple deployment
- ✅ Great UI/UX
- ✅ No timeout issues

### **Deployment Steps:**

#### **Step 1: Install Railway CLI**

```bash
# Windows
npm install -g @railway/cli

# Or use the website (easier)
```

#### **Step 2: Deploy**

```bash
# Method 1: CLI
railway login
railway init
railway up

# Method 2: Website (Recommended)
# 1. Go to https://railway.app
# 2. Sign up (GitHub login)
# 3. New Project → Deploy from GitHub repo
# 4. Select your repository
# 5. Done!
```

#### **Step 3: Add Environment Variables**

In Railway dashboard:

```
USE_GCS_STORAGE=true
GCS_PROJECT_ID=focus-cumulus-477711-g5
GCS_BUCKET_NAME=ap_cctv_test_bucket
IMAGES_DIR=test
MAX_WORKERS=5
OPENAI_API_KEY=your_key_here
```

#### **Step 4: Add GCS Key**

Upload `gcs-key.json` content as environment variable:

```
GOOGLE_APPLICATION_CREDENTIALS=/app/gcs-key.json
```

**Your URL:**
```
https://cctv-analyzer.railway.app
```

---

## ✈️ **Option 3: Fly.io**

### **Why Fly.io?**
- ✅ **3 free VMs (256 MB each)**
- ✅ Global edge deployment
- ✅ Docker-based
- ✅ Good performance

### **Deployment Steps:**

#### **Step 1: Install Fly CLI**

```bash
# Windows (PowerShell)
powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"

# Linux/Mac
curl -L https://fly.io/install.sh | sh
```

#### **Step 2: Login and Setup**

```bash
# Login
fly auth login

# Create app
fly launch

# Answer prompts:
# - App name: cctv-analyzer
# - Region: Choose closest
# - Database: No
# - Deploy now: No (we'll configure first)
```

#### **Step 3: Set Secrets**

```bash
# Set secrets
fly secrets set OPENAI_API_KEY=your_key_here
fly secrets set USE_GCS_STORAGE=true
fly secrets set GCS_PROJECT_ID=focus-cumulus-477711-g5
fly secrets set GCS_BUCKET_NAME=ap_cctv_test_bucket

# Upload GCS key
fly secrets set GOOGLE_APPLICATION_CREDENTIALS="$(cat gcs-key.json)"
```

#### **Step 4: Deploy**

```bash
fly deploy
```

**Your URL:**
```
https://cctv-analyzer.fly.dev
```

---

## 📦 **Option 4: Vercel (With Limitations)**

### **⚠️ Warning: Timeout Issues!**

Vercel **will timeout** on long analyses. Use only if:
- Analyzing <5 images at a time
- Quick analysis only
- Or use for frontend + another backend

### **If You Still Want to Try:**

#### **Step 1: Prepare**

```bash
# Install Vercel CLI
npm install -g vercel

# Make sure vercel.json exists (already created ✅)
```

#### **Step 2: Deploy**

```bash
# Login
vercel login

# Deploy
vercel

# Follow prompts
```

#### **Step 3: Add Environment Variables**

```bash
vercel env add OPENAI_API_KEY
vercel env add USE_GCS_STORAGE
vercel env add GCS_PROJECT_ID
vercel env add GCS_BUCKET_NAME
```

**Your URL:**
```
https://cctv-analyzer.vercel.app
```

**Note:** Expect timeouts on multiple images!

---

## 📊 **Feature Comparison**

| Feature | Render | Railway | Fly.io | Vercel |
|---------|--------|---------|--------|--------|
| **Free Tier** | 750 hrs | $5 credit | 3 VMs | Unlimited |
| **Timeout** | None ✅ | None ✅ | None ✅ | 10-60s ❌ |
| **Flask Support** | Excellent | Excellent | Good | Limited |
| **GCS Integration** | Yes ✅ | Yes ✅ | Yes ✅ | Yes ✅ |
| **Auto Deploy** | Yes ✅ | Yes ✅ | Manual | Yes ✅ |
| **Custom Domain** | Yes ✅ | Yes ✅ | Yes ✅ | Yes ✅ |
| **Best For** | **This app!** | Good choice | Good choice | Frontend only |

---

## 💰 **Cost Comparison (Monthly)**

| Platform | Free Tier | Enough for 24/7? | Overages |
|----------|-----------|------------------|----------|
| **Render.com** | 750 hours | ✅ Yes! | Sleep after 15 min idle |
| **Railway.app** | $5 credit (~500 hrs) | ✅ Yes! | $0.01/min after |
| **Fly.io** | 3 VMs (256 MB) | ✅ Yes! | $1.94/mo per VM |
| **Vercel** | Unlimited | ⚠️ Timeouts | Function limits |

---

## 🎯 **Recommendation**

### **Best Choice: Render.com**

**Why?**
1. ✅ **Most generous free tier** (750 hours)
2. ✅ **No timeout issues** (perfect for AI)
3. ✅ **Easy deployment** (connects to GitHub)
4. ✅ **Great for Flask** (designed for Python)
5. ✅ **Still uses GCS** (no storage issues)

### **Quick Start:**

```bash
# 1. Push code to GitHub
git add .
git commit -m "Deploy to Render"
git push origin main

# 2. Go to https://render.com
# 3. Sign up (free)
# 4. New Web Service → Connect GitHub
# 5. Add environment variables
# 6. Deploy!

# Done in 5 minutes! ✅
```

---

## 🔧 **Important: GCS Still Required**

**All these platforms use GCS for images:**
- Server: Deployed on Render/Railway/Fly
- Images: Stored in your GCS bucket
- Storage: 0 MB on server (lazy loading)

**Why?**
- ✅ Even free platforms have storage limits
- ✅ GCS provides unlimited image storage
- ✅ Lazy loading keeps server light
- ✅ Perfect combination!

**GCS Cost:**
- 100 GB: $2/month
- 1 TB: $20/month
- Worth it for unlimited images!

---

## 📋 **Deployment Checklist**

Before deploying:

- [ ] Code pushed to GitHub
- [ ] `requirements.txt` has `gunicorn`
- [ ] Images uploaded to GCS
- [ ] `gcs-key.json` file ready
- [ ] OpenAI API key ready
- [ ] Choose platform (Render recommended)

---

## 🚀 **Quick Deployment (Render)**

### **5-Minute Setup:**

```bash
# 1. Push to GitHub
git add .
git commit -m "Ready for deployment"
git push origin main

# 2. Go to Render.com
# https://render.com

# 3. Sign up (free)

# 4. New Web Service
# - Connect GitHub repo
# - Name: cctv-analyzer
# - Build: pip install -r requirements.txt
# - Start: gunicorn flask_app:app --bind 0.0.0.0:$PORT

# 5. Add environment variables:
USE_GCS_STORAGE=true
GCS_PROJECT_ID=focus-cumulus-477711-g5
GCS_BUCKET_NAME=ap_cctv_test_bucket
OPENAI_API_KEY=your_key
# Upload gcs-key.json

# 6. Click Create Web Service

# Done! ✅
```

**Your app will be live at:**
```
https://cctv-analyzer.onrender.com
```

---

## 📝 **Files Created**

- ✅ `render.yaml` - Render configuration
- ✅ `railway.json` - Railway configuration
- ✅ `fly.toml` - Fly.io configuration
- ✅ `vercel.json` - Vercel configuration
- ✅ `DEPLOY_FREE.md` - This guide

---

## 🎉 **Summary**

### **Best FREE Solution:**

```
Platform: Render.com
Cost: $0/month (750 hours)
Images: GCS (still needed)
Storage on server: 0 MB
Timeout: None
Perfect for: This app! ✅
```

### **Why This Works:**

1. ✅ **Free hosting** on Render
2. ✅ **Images in GCS** (unlimited)
3. ✅ **Lazy loading** (no storage issues)
4. ✅ **No timeouts** (unlike Vercel)
5. ✅ **Easy deployment** (5 minutes)

---

## 🆘 **Need Help?**

### **Test Locally First:**

```bash
# Install gunicorn
pip install gunicorn

# Test production command
gunicorn flask_app:app --bind 0.0.0.0:5000

# Open: http://localhost:5000
```

### **Deploy to Render:**

```
1. https://render.com → Sign up
2. New Web Service → Connect GitHub
3. Add env vars
4. Deploy
```

---

## ✨ **Bottom Line**

**For FREE deployment:**
- ⭐ **Use Render.com** (best choice)
- ⚠️ **Avoid Vercel** (timeout issues)
- ✅ **Keep images in GCS** (still needed)
- 🎉 **Total cost: $0-2/month!**

**Deploy now:**
```
https://render.com → 5 minutes → Done! ✅
```

