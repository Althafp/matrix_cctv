"""
Upload Images to Google Cloud Storage (GCS)
Upload all images from local directory to GCS bucket
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import storage
from tqdm import tqdm
import time

# Load environment variables
load_dotenv()


def upload_images_to_gcs():
    """Upload all images from local directory to GCS bucket"""
    
    print("\n" + "="*70)
    print("📤 UPLOAD IMAGES TO GOOGLE CLOUD STORAGE")
    print("="*70)
    
    # Load configuration from .env
    use_gcs = os.getenv('USE_GCS_STORAGE', 'false').lower() == 'true'
    project_id = os.getenv('GCS_PROJECT_ID')
    bucket_name = os.getenv('GCS_BUCKET_NAME')
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    images_dir = os.getenv('IMAGES_DIR', 'test')
    
    # Validate configuration
    if not use_gcs:
        print("\n⚠️  GCS is disabled in .env file!")
        print("   Set USE_GCS_STORAGE=true to enable GCS")
        return False
    
    if not all([project_id, bucket_name, credentials_path]):
        print("\n❌ Missing GCS configuration in .env file!")
        print("\nRequired variables:")
        print("  - GCS_PROJECT_ID")
        print("  - GCS_BUCKET_NAME")
        print("  - GOOGLE_APPLICATION_CREDENTIALS")
        return False
    
    print(f"\n📋 Configuration:")
    print(f"   Project ID: {project_id}")
    print(f"   Bucket: {bucket_name}")
    print(f"   Credentials: {credentials_path}")
    print(f"   Local Directory: {images_dir}/")
    
    # Check if credentials file exists
    if not Path(credentials_path).exists():
        print(f"\n❌ Credentials file not found: {credentials_path}")
        print("\nPlease download your service account key:")
        print("   1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts")
        print("   2. Select your service account")
        print("   3. Click 'Keys' → 'Add Key' → 'Create new key'")
        print("   4. Choose JSON format")
        print(f"   5. Save as: {credentials_path}")
        return False
    
    # Check if local directory exists
    local_path = Path(images_dir)
    if not local_path.exists():
        print(f"\n❌ Local directory not found: {images_dir}/")
        print("\nPlease ensure your images are in this directory")
        return False
    
    # Get all image files
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
    image_files = []
    for ext in image_extensions:
        image_files.extend(local_path.glob(ext))
    
    if not image_files:
        print(f"\n⚠️  No images found in {images_dir}/")
        print(f"   Searched for: {', '.join(image_extensions)}")
        return False
    
    print(f"\n📸 Found {len(image_files)} images to upload")
    
    # Show sample files
    print(f"\n   Sample files:")
    for img in image_files[:5]:
        print(f"   - {img.name}")
    if len(image_files) > 5:
        print(f"   ... and {len(image_files) - 5} more")
    
    # Ask for confirmation
    print(f"\n📦 Upload destination: gs://{bucket_name}/{images_dir}/")
    
    confirm = input("\n❓ Do you want to proceed with upload? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y']:
        print("\n❌ Upload cancelled by user")
        return False
    
    # Initialize GCS client
    try:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        client = storage.Client(project=project_id)
        bucket = client.bucket(bucket_name)
        
        # Test bucket access
        if not bucket.exists():
            print(f"\n❌ Bucket '{bucket_name}' does not exist or is not accessible!")
            print("\nPlease verify:")
            print("   1. Bucket name is correct")
            print("   2. Service account has access to the bucket")
            print("   3. Bucket exists in your project")
            return False
        
        print(f"\n✅ Successfully connected to bucket: {bucket_name}")
        
    except Exception as e:
        print(f"\n❌ Failed to connect to GCS: {e}")
        print("\nPlease check:")
        print("   1. Credentials file is valid")
        print("   2. Project ID is correct")
        print("   3. You have internet connection")
        return False
    
    # Upload images with progress bar
    print(f"\n📤 Uploading {len(image_files)} images...")
    print("=" * 70)
    
    uploaded = 0
    skipped = 0
    failed = 0
    
    start_time = time.time()
    
    with tqdm(total=len(image_files), desc="Uploading", unit="img") as pbar:
        for image_path in image_files:
            try:
                # Destination blob name (preserves directory structure)
                blob_name = f"{images_dir}/{image_path.name}"
                blob = bucket.blob(blob_name)
                
                # Check if already exists (optional: skip or overwrite)
                if blob.exists():
                    skipped += 1
                    tqdm.write(f"  ⏭️  Skipped (already exists): {image_path.name}")
                else:
                    # Upload the file
                    blob.upload_from_filename(str(image_path))
                    uploaded += 1
                    tqdm.write(f"  ✅ Uploaded: {image_path.name}")
                
                pbar.update(1)
                
            except Exception as e:
                failed += 1
                tqdm.write(f"  ❌ Failed: {image_path.name} - {str(e)}")
                pbar.update(1)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Summary
    print("\n" + "="*70)
    print("📊 UPLOAD SUMMARY")
    print("="*70)
    print(f"\n✅ Successfully uploaded: {uploaded} images")
    print(f"⏭️  Skipped (already exist): {skipped} images")
    
    if failed > 0:
        print(f"❌ Failed: {failed} images")
    
    print(f"\n⏱️  Time taken: {duration:.2f} seconds")
    
    if uploaded > 0:
        print(f"⚡ Average speed: {duration/uploaded:.2f} seconds per image")
    
    print(f"\n🌐 View your bucket:")
    print(f"   https://console.cloud.google.com/storage/browser/{bucket_name}/{images_dir}")
    
    print("\n" + "="*70)
    print("✅ UPLOAD COMPLETE!")
    print("="*70)
    
    # Next steps
    print("\n📋 Next Steps:")
    print("   1. Verify images in GCS Console (link above)")
    print("   2. Run: python flask_app.py")
    print("   3. Open: http://localhost:5000")
    print("   4. Start analyzing your images! 🚀")
    
    return True


def upload_with_overwrite():
    """Upload images and overwrite existing ones"""
    
    print("\n" + "="*70)
    print("📤 UPLOAD IMAGES TO GCS (OVERWRITE MODE)")
    print("="*70)
    
    # Load configuration
    use_gcs = os.getenv('USE_GCS_STORAGE', 'false').lower() == 'true'
    if not use_gcs:
        print("\n⚠️  GCS is disabled in .env file!")
        return False
    
    project_id = os.getenv('GCS_PROJECT_ID')
    bucket_name = os.getenv('GCS_BUCKET_NAME')
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    images_dir = os.getenv('IMAGES_DIR', 'test')
    
    # Get image files
    local_path = Path(images_dir)
    if not local_path.exists():
        print(f"\n❌ Directory not found: {images_dir}/")
        return False
    
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
    image_files = []
    for ext in image_extensions:
        image_files.extend(local_path.glob(ext))
    
    if not image_files:
        print(f"\n⚠️  No images found in {images_dir}/")
        return False
    
    print(f"\n📸 Found {len(image_files)} images")
    print(f"📦 Destination: gs://{bucket_name}/{images_dir}/")
    print("\n⚠️  WARNING: This will overwrite existing files!")
    
    confirm = input("\n❓ Continue? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y']:
        print("\n❌ Upload cancelled")
        return False
    
    # Initialize GCS
    try:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        client = storage.Client(project=project_id)
        bucket = client.bucket(bucket_name)
        
        if not bucket.exists():
            print(f"\n❌ Bucket not found: {bucket_name}")
            return False
        
        print(f"\n✅ Connected to bucket: {bucket_name}")
        
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        return False
    
    # Upload with overwrite
    print(f"\n📤 Uploading (overwrite mode)...")
    uploaded = 0
    failed = 0
    
    with tqdm(total=len(image_files), desc="Uploading", unit="img") as pbar:
        for image_path in image_files:
            try:
                blob_name = f"{images_dir}/{image_path.name}"
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(str(image_path))
                uploaded += 1
                tqdm.write(f"  ✅ Uploaded: {image_path.name}")
                pbar.update(1)
                
            except Exception as e:
                failed += 1
                tqdm.write(f"  ❌ Failed: {image_path.name} - {str(e)}")
                pbar.update(1)
    
    print(f"\n✅ Uploaded: {uploaded}")
    if failed > 0:
        print(f"❌ Failed: {failed}")
    
    print("\n✅ Done!")
    return True


def list_bucket_contents():
    """List all files currently in the GCS bucket"""
    
    print("\n" + "="*70)
    print("📂 LIST BUCKET CONTENTS")
    print("="*70)
    
    # Load configuration
    use_gcs = os.getenv('USE_GCS_STORAGE', 'false').lower() == 'true'
    if not use_gcs:
        print("\n⚠️  GCS is disabled in .env file!")
        return False
    
    project_id = os.getenv('GCS_PROJECT_ID')
    bucket_name = os.getenv('GCS_BUCKET_NAME')
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    images_dir = os.getenv('IMAGES_DIR', 'test')
    
    try:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        client = storage.Client(project=project_id)
        bucket = client.bucket(bucket_name)
        
        print(f"\n📦 Bucket: {bucket_name}")
        print(f"📁 Prefix: {images_dir}/")
        
        blobs = list(bucket.list_blobs(prefix=f"{images_dir}/"))
        
        if not blobs:
            print(f"\n⚠️  No files found with prefix '{images_dir}/'")
            return False
        
        print(f"\n✅ Found {len(blobs)} files:\n")
        
        for i, blob in enumerate(blobs, 1):
            size_mb = blob.size / (1024 * 1024)
            print(f"   {i}. {blob.name} ({size_mb:.2f} MB)")
        
        print(f"\n🌐 View in console:")
        print(f"   https://console.cloud.google.com/storage/browser/{bucket_name}/{images_dir}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def main():
    """Main menu"""
    
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║           GCS IMAGE UPLOAD UTILITY                                ║
║           Upload local images to Google Cloud Storage             ║
╚═══════════════════════════════════════════════════════════════════╝
""")
    
    print("Select an option:")
    print("  1. Upload images (skip existing)")
    print("  2. Upload images (overwrite existing)")
    print("  3. List bucket contents")
    print("  4. Exit")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == '1':
        upload_images_to_gcs()
    elif choice == '2':
        upload_with_overwrite()
    elif choice == '3':
        list_bucket_contents()
    elif choice == '4':
        print("\n👋 Goodbye!")
    else:
        print("\n❌ Invalid choice!")


if __name__ == "__main__":
    main()

