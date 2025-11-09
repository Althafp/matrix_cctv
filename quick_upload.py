"""
Quick Upload Script - Upload images to GCS in one command
Usage: python quick_upload.py
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import storage
from tqdm import tqdm

load_dotenv()


def quick_upload():
    """Quick upload all images from test/ to GCS bucket"""
    
    # Configuration from .env
    project_id = os.getenv('GCS_PROJECT_ID', 'focus-cumulus-477711-g5')
    bucket_name = os.getenv('GCS_BUCKET_NAME', 'ap_cctv_test_bucket')
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'gcs-key.json')
    images_dir = os.getenv('IMAGES_DIR', 'test')
    
    print(f"\n🚀 Quick Upload to GCS")
    print(f"   Bucket: {bucket_name}")
    print(f"   From: {images_dir}/ → gs://{bucket_name}/{images_dir}/\n")
    
    # Check credentials
    if not Path(credentials_path).exists():
        print(f"❌ Error: {credentials_path} not found!")
        print("\n📥 Download your service account key:")
        print("   1. Visit: https://console.cloud.google.com/iam-admin/serviceaccounts")
        print("   2. Select service account → Keys → Add Key → Create")
        print(f"   3. Save as: {credentials_path}")
        return
    
    # Check images directory
    local_path = Path(images_dir)
    if not local_path.exists():
        print(f"❌ Error: Directory '{images_dir}/' not found!")
        return
    
    # Get image files
    image_files = (
        list(local_path.glob("*.jpg")) + 
        list(local_path.glob("*.jpeg")) + 
        list(local_path.glob("*.png"))
    )
    
    if not image_files:
        print(f"❌ No images found in {images_dir}/")
        return
    
    print(f"📸 Found {len(image_files)} images\n")
    
    # Connect to GCS
    try:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        client = storage.Client(project=project_id)
        bucket = client.bucket(bucket_name)
        
        if not bucket.exists():
            print(f"❌ Error: Bucket '{bucket_name}' not found!")
            print("\n📦 Create bucket:")
            print(f"   https://console.cloud.google.com/storage/browser?project={project_id}")
            return
        
        print(f"✅ Connected to bucket: {bucket_name}\n")
        
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return
    
    # Upload with progress
    print("📤 Uploading...\n")
    
    uploaded = 0
    skipped = 0
    
    for image_path in tqdm(image_files, desc="Progress", unit="img"):
        blob_name = f"{images_dir}/{image_path.name}"
        blob = bucket.blob(blob_name)
        
        # Skip if exists (change to blob.upload_from_filename() to overwrite)
        if blob.exists():
            skipped += 1
        else:
            blob.upload_from_filename(str(image_path))
            uploaded += 1
    
    # Summary
    print(f"\n✅ Upload complete!")
    print(f"   Uploaded: {uploaded}")
    print(f"   Skipped: {skipped} (already exist)")
    
    print(f"\n🌐 View in GCS Console:")
    print(f"   https://console.cloud.google.com/storage/browser/{bucket_name}/{images_dir}\n")
    
    print("🎉 Next step: Run 'python flask_app.py' to start analyzing!\n")


if __name__ == "__main__":
    quick_upload()

