# 📤 Upload Images to Google Cloud Storage

Quick guide to upload your local images to GCS bucket.

---

## 🚀 **Quick Method (Recommended)**

### **Single Command Upload:**

```bash
python quick_upload.py
```

This will:
- ✅ Upload all images from `test/` folder
- ✅ Skip images that already exist in bucket
- ✅ Show progress bar
- ✅ Give you a summary

**Output:**
```
🚀 Quick Upload to GCS
   Bucket: ap_cctv_test_bucket
   From: test/ → gs://ap_cctv_test_bucket/test/

📸 Found 20 images

✅ Connected to bucket: ap_cctv_test_bucket

📤 Uploading...
Progress: 100%|████████████████████| 20/20 [00:15<00:00,  1.33img/s]

✅ Upload complete!
   Uploaded: 20
   Skipped: 0 (already exist)

🌐 View in GCS Console:
   https://console.cloud.google.com/storage/browser/ap_cctv_test_bucket/test
```

---

## 🎯 **Interactive Method (More Options)**

### **Run Interactive Upload Script:**

```bash
python upload_to_gcs.py
```

**Menu Options:**
```
╔═══════════════════════════════════════════════════════════════════╗
║           GCS IMAGE UPLOAD UTILITY                                ║
║           Upload local images to Google Cloud Storage             ║
╚═══════════════════════════════════════════════════════════════════╝

Select an option:
  1. Upload images (skip existing)      ← Safe, won't overwrite
  2. Upload images (overwrite existing)  ← Updates all files
  3. List bucket contents                ← See what's in bucket
  4. Exit
```

### **Option 1: Upload (Skip Existing)**
- Uploads new images only
- **Safe**: Won't overwrite existing files
- **Fast**: Skips duplicates

### **Option 2: Upload (Overwrite)**
- Uploads all images
- **Updates**: Replaces existing files
- **Use when**: Images have been updated locally

### **Option 3: List Contents**
- Shows all files in your bucket
- Check what's already uploaded
- See file sizes

---

## 📋 **Before You Upload**

### **1. Check Your Configuration**

Make sure your `.env` file has:
```bash
USE_GCS_STORAGE=true
GCS_PROJECT_ID=focus-cumulus-477711-g5
GOOGLE_APPLICATION_CREDENTIALS=gcs-key.json
GCS_BUCKET_NAME=ap_cctv_test_bucket
IMAGES_DIR=test
```

### **2. Verify Credentials File**

Check that `gcs-key.json` exists:
```bash
# Windows
dir gcs-key.json

# Linux/Mac
ls gcs-key.json
```

If not found:
1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts?project=focus-cumulus-477711-g5
2. Click your service account
3. Keys tab → Add Key → Create new key
4. Choose JSON → Download
5. Save as `gcs-key.json` in project root

### **3. Check Images Directory**

Verify images are in the right folder:
```bash
# Windows
dir test\*.jpg

# Linux/Mac
ls test/*.jpg
```

---

## 🎬 **Step-by-Step Upload Process**

### **Method 1: Quick Upload (Fastest)**

```bash
# Step 1: Run upload script
python quick_upload.py

# Step 2: Wait for completion (shows progress bar)

# Step 3: Verify in GCS Console
# Opens automatically or use link from output
```

### **Method 2: Interactive Upload (More Control)**

```bash
# Step 1: Run interactive script
python upload_to_gcs.py

# Step 2: Choose option 1 (skip existing)

# Step 3: Review summary
📋 Configuration:
   Project ID: focus-cumulus-477711-g5
   Bucket: ap_cctv_test_bucket
   Credentials: gcs-key.json
   Local Directory: test/

📸 Found 20 images to upload

   Sample files:
   - 3_Roads_Junction_Kothapea_10_247_8_160_20251108_131958.jpg
   - 3_STATUE_CENTER_NAGARAMPALEM_10_246_10_3_20251108_124617.jpg
   ... and 18 more

📦 Upload destination: gs://ap_cctv_test_bucket/test/

# Step 4: Confirm
❓ Do you want to proceed with upload? (yes/no): yes

# Step 5: Wait for upload
📤 Uploading 20 images...
  ✅ Uploaded: 3_Roads_Junction_Kothapea_10_247_8_160_20251108_131958.jpg
  ✅ Uploaded: 3_STATUE_CENTER_NAGARAMPALEM_10_246_10_3_20251108_124617.jpg
  ...

# Step 6: Check summary
📊 UPLOAD SUMMARY
✅ Successfully uploaded: 20 images
⏭️  Skipped (already exist): 0 images
⏱️  Time taken: 45.23 seconds
```

---

## 🔍 **Verify Upload**

### **Option 1: Using Script**
```bash
python upload_to_gcs.py
# Choose option 3: List bucket contents
```

### **Option 2: GCS Console**
1. Open: https://console.cloud.google.com/storage/browser/ap_cctv_test_bucket
2. Click `test/` folder
3. You should see all your images

### **Option 3: Using gsutil (if installed)**
```bash
gsutil ls gs://ap_cctv_test_bucket/test/
```

---

## ⚡ **Quick Commands**

```bash
# Quick upload (skip existing)
python quick_upload.py

# Interactive menu
python upload_to_gcs.py

# List what's in bucket
python upload_to_gcs.py
# Then choose option 3

# Test GCS connection
python gcs_storage.py

# Start Flask app (after upload)
python flask_app.py
```

---

## 🔧 **Troubleshooting**

### **Problem: "Credentials file not found"**

```bash
# Check if file exists
ls gcs-key.json

# If not, download from:
# https://console.cloud.google.com/iam-admin/serviceaccounts
```

### **Problem: "Bucket not found"**

```bash
# Verify bucket name in .env
echo $GCS_BUCKET_NAME  # Linux/Mac
echo %GCS_BUCKET_NAME%  # Windows

# Check bucket exists:
# https://console.cloud.google.com/storage/browser
```

### **Problem: "Permission denied"**

Solution:
1. Service account needs "Storage Object Admin" role
2. Go to: https://console.cloud.google.com/iam-admin/iam
3. Find your service account
4. Add role: "Storage Object Admin"

### **Problem: "No images found"**

```bash
# Check images are in correct directory
ls test/*.jpg

# Verify IMAGES_DIR in .env
# Should match your folder name
```

### **Problem: "Upload is slow"**

- Normal for many/large images
- Typical: 1-2 seconds per image
- For 20 images: expect 30-60 seconds
- Check internet speed

---

## 📊 **Upload Times (Approximate)**

| Images | Size | Time | Speed |
|--------|------|------|-------|
| 10 | ~2 MB each | ~20s | Fast |
| 20 | ~2 MB each | ~40s | Normal |
| 50 | ~2 MB each | ~2min | Expected |
| 100 | ~2 MB each | ~4min | Be patient |

---

## 🎯 **After Upload**

### **1. Verify Images**
```bash
# List bucket contents
python upload_to_gcs.py
# Choose option 3
```

### **2. Test Download**
```bash
# Download images from GCS
python gcs_storage.py
```

### **3. Start Flask App**
```bash
# Run the analyzer
python flask_app.py

# Open browser
# http://localhost:5000
```

### **4. Analyze Images**
- Create new session
- Type your question
- Watch real-time analysis!

---

## 💡 **Tips**

### **Incremental Uploads**
- Upload new images only
- Existing images are skipped automatically
- No need to delete bucket first

### **Update Images**
- Use **Option 2** (overwrite mode)
- Updates all files in bucket
- Use when local images changed

### **Organize Images**
```
Your folder structure:
test/
├── image1.jpg
├── image2.jpg
└── ...

Becomes in GCS:
gs://ap_cctv_test_bucket/
└── test/
    ├── image1.jpg
    ├── image2.jpg
    └── ...
```

### **Cost Optimization**
- GCS charges for storage ($0.02/GB/month)
- 20 images (~40 MB) = ~$0.001/month
- Very affordable!

---

## 🔄 **Workflow**

```
1. Add images to test/ folder
        ↓
2. Run: python quick_upload.py
        ↓
3. Verify in GCS Console
        ↓
4. Run: python flask_app.py
        ↓
5. Analyze at http://localhost:5000
        ↓
6. Repeat as needed!
```

---

## ✅ **Success Checklist**

Before running the app:
- [ ] Images uploaded to GCS bucket
- [ ] Can see images in GCS Console
- [ ] `gcs-key.json` exists in project root
- [ ] `.env` configured correctly
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Test connection successful (`python gcs_storage.py`)

---

## 🎉 **You're Ready!**

Once upload is complete:

```bash
python flask_app.py
```

The app will:
1. Connect to GCS
2. Download images to cache
3. Initialize analyzer
4. Start web server

Then visit: **http://localhost:5000** 🚀

---

## 📞 **Need Help?**

**Check upload status:**
```bash
python upload_to_gcs.py
# Choose option 3: List bucket contents
```

**View in browser:**
```
https://console.cloud.google.com/storage/browser/ap_cctv_test_bucket/test
```

**Test connection:**
```bash
python gcs_storage.py
```

---

Happy Uploading! 📤✨

