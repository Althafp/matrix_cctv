# 📤 Upload to GitHub

## 🚀 **Quick Git Upload Commands**

```bash
# 1. Initialize git (if not done)
git init

# 2. Add all files
git add .

# 3. Commit
git commit -m "Initial commit: CCTV Camera Analyzer with Zero Download Mode"

# 4. Add remote repository
git remote add origin https://github.com/Althafp/matrix_cctv.git

# 5. Push to GitHub
git branch -M main
git push -u origin main
```

---

## 📋 **Step-by-Step**

### **Step 1: Check Git Status**
```bash
git init
git status
```

### **Step 2: Add Files**
```bash
# Add all files
git add .

# Or add specific files only
git add flask_app.py camera_analyzer.py gcs_storage.py
git add requirements.txt .gitignore README.md
git add templates/ static/
```

### **Step 3: Commit**
```bash
git commit -m "Initial commit: CCTV Analyzer with Zero Download"
```

### **Step 4: Connect to GitHub**
```bash
git remote add origin https://github.com/Althafp/matrix_cctv.git
```

### **Step 5: Push**
```bash
# Set main branch
git branch -M main

# Push to GitHub
git push -u origin main
```

---

## ⚠️ **Important: Exclude Sensitive Files**

Make sure these are **NOT** uploaded (already in `.gitignore`):

- ❌ `.env` (contains secrets)
- ❌ `gcs-key.json` (service account key)
- ❌ `a_test/` images (if you have them locally)
- ❌ `test/` images
- ❌ `gcs_cache/` (cache folder)
- ❌ `sessions/` (user data)

---

## ✅ **Verification**

After pushing, visit:
```
https://github.com/Althafp/matrix_cctv
```

You should see all your files! ✅

---

## 🔄 **Update Later**

```bash
# Make changes to your code

# Add changes
git add .

# Commit
git commit -m "Your update message"

# Push
git push
```

---

## 📦 **Complete Command**

Copy-paste this entire block:

```bash
git init
git add .
git commit -m "Initial commit: CCTV Camera Analyzer with Zero Download Mode - Production ready Flask app with GCS integration"
git remote add origin https://github.com/Althafp/matrix_cctv.git
git branch -M main
git push -u origin main
```

---

Done! 🎉

