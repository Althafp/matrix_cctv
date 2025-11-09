"""
Google Cloud Storage (GCS) Integration Module
Handles fetching images from GCS bucket with lazy loading (on-demand downloads)
"""

import os
import io
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
from google.cloud import storage
import tempfile
import time

load_dotenv()


class GCSStorageManager:
    """Manages Google Cloud Storage operations for camera images"""
    
    def __init__(self, lazy_load=True):
        """
        Initialize GCS client
        
        Args:
            lazy_load: If True, don't download all images upfront (default: True)
                      Images are downloaded on-demand during analysis
        """
        self.use_gcs = os.getenv('USE_GCS_STORAGE', 'false').lower() == 'true'
        self.lazy_load = lazy_load
        
        if not self.use_gcs:
            print("📁 Using local storage (USE_GCS_STORAGE=false)")
            return
        
        # GCS Configuration
        self.project_id = os.getenv('GCS_PROJECT_ID')
        self.bucket_name = os.getenv('GCS_BUCKET_NAME')
        self.credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        # Validate configuration (credentials optional on Cloud Run)
        if not all([self.project_id, self.bucket_name]):
            raise ValueError(
                "Missing GCS configuration! Required in .env:\n"
                "  - GCS_PROJECT_ID\n"
                "  - GCS_BUCKET_NAME"
            )
        
        # Set credentials if provided (for local development)
        # On Cloud Run, default service account is used automatically
        if self.credentials_path and os.path.exists(self.credentials_path):
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.credentials_path
            print(f"🔑 Using credentials from: {self.credentials_path}")
        else:
            print(f"🔑 Using default GCP service account (Cloud Run)"))
        
        # Initialize client
        try:
            self.client = storage.Client(project=self.project_id)
            self.bucket = self.client.bucket(self.bucket_name)
            
            # Test connection
            if self.bucket.exists():
                print(f"\n{'='*60}")
                print("☁️  Google Cloud Storage Connected Successfully!")
                print(f"📦 Bucket: {self.bucket_name}")
                print(f"🔑 Project: {self.project_id}")
                print(f"{'='*60}\n")
            else:
                raise ValueError(f"Bucket '{self.bucket_name}' does not exist!")
                
        except Exception as e:
            print(f"\n❌ Failed to connect to GCS: {e}")
            print("Falling back to local storage...")
            self.use_gcs = False
        
        # Local cache directory
        self.cache_dir = Path("gcs_cache")
        self.cache_dir.mkdir(exist_ok=True)
        
        # Image list cache (to avoid repeated API calls)
        self._image_list_cache = None
        self._cache_timestamp = None
    
    def list_images(self, prefix: str = "", extensions: List[str] = ['.jpg', '.jpeg', '.png'], use_cache: bool = True) -> List[str]:
        """
        List all images in the bucket with given prefix (cached for 5 minutes)
        
        Args:
            prefix: Directory prefix in bucket (e.g., "test/")
            extensions: List of image extensions to filter
            use_cache: Use cached list if available (default: True)
            
        Returns:
            List of image blob names
        """
        if not self.use_gcs:
            return []
        
        # Check cache
        if use_cache and self._image_list_cache is not None and self._cache_timestamp:
            cache_age = time.time() - self._cache_timestamp
            if cache_age < 300:  # 5 minutes
                return self._image_list_cache
        
        try:
            print(f"📂 Listing images from GCS bucket '{self.bucket_name}'...")
            if prefix:
                print(f"   Prefix: {prefix}")
            
            blobs = self.bucket.list_blobs(prefix=prefix)
            image_names = []
            
            for blob in blobs:
                # Check if file has image extension
                if any(blob.name.lower().endswith(ext) for ext in extensions):
                    image_names.append(blob.name)
            
            print(f"✅ Found {len(image_names)} images in GCS bucket")
            
            # Show sample files (only for small counts)
            if image_names and len(image_names) <= 10:
                print(f"   Sample files:")
                for name in image_names[:3]:
                    print(f"   - {name}")
                if len(image_names) > 3:
                    print(f"   ... and {len(image_names) - 3} more")
            
            # Cache the result
            self._image_list_cache = image_names
            self._cache_timestamp = time.time()
            
            return image_names
            
        except Exception as e:
            print(f"❌ Error listing images from GCS: {e}")
            return []
    
    def download_image(self, blob_name: str, local_path: Optional[Path] = None) -> Optional[Path]:
        """
        Download an image from GCS to local storage (ONLY for fallback)
        NOTE: In ZERO DOWNLOAD mode, this is rarely used
        
        Args:
            blob_name: Name of the blob in GCS
            local_path: Optional local path to save the file
            
        Returns:
            Path to the downloaded file or None if failed
        """
        if not self.use_gcs:
            return None
        
        try:
            # Use cache directory if no local path specified
            if local_path is None:
                # Preserve directory structure in cache
                local_path = self.cache_dir / blob_name
                local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # DON'T cache - always download fresh for fallback cases
            # (This method is rarely called in ZERO DOWNLOAD mode)
            
            # Download from GCS
            blob = self.bucket.blob(blob_name)
            blob.download_to_filename(str(local_path))
            
            return local_path
            
        except Exception as e:
            print(f"❌ Error downloading {blob_name}: {e}")
            return None
    
    def download_image_to_memory(self, blob_name: str) -> Optional[bytes]:
        """
        Download an image from GCS directly to memory (no disk write)
        ⚡ Fast and efficient - no local storage needed!
        
        Args:
            blob_name: Name of the blob in GCS
            
        Returns:
            Image bytes or None if failed
        """
        if not self.use_gcs:
            return None
        
        try:
            blob = self.bucket.blob(blob_name)
            image_bytes = blob.download_as_bytes()
            return image_bytes
            
        except Exception as e:
            print(f"❌ Error downloading {blob_name} to memory: {e}")
            return None
    
    def get_image_as_path_object(self, blob_name: str) -> Optional[Path]:
        """
        Get a Path-like object for a GCS image (downloads only if needed)
        Used for lazy loading during analysis
        
        Args:
            blob_name: Name of the blob in GCS
            
        Returns:
            Path to cached image or None if failed
        """
        if not self.use_gcs:
            return None
        
        # Check if already in cache
        cache_path = self.cache_dir / blob_name
        if cache_path.exists():
            return cache_path
        
        # Download on-demand
        return self.download_image(blob_name)
    
    def download_all_images(self, prefix: str = "", force_refresh: bool = False) -> List[Path]:
        """
        Download all images with given prefix to local cache
        
        Args:
            prefix: Directory prefix in bucket
            force_refresh: If True, re-download even if cached
            
        Returns:
            List of local file paths
        """
        if not self.use_gcs:
            return []
        
        try:
            image_names = self.list_images(prefix=prefix)
            
            if not image_names:
                print("⚠️  No images found in GCS bucket")
                return []
            
            print(f"\n📥 Downloading {len(image_names)} images from GCS...")
            
            local_paths = []
            downloaded = 0
            cached = 0
            
            for blob_name in image_names:
                local_path = self.cache_dir / blob_name
                local_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Check if already cached
                if local_path.exists() and not force_refresh:
                    local_paths.append(local_path)
                    cached += 1
                else:
                    # Download
                    blob = self.bucket.blob(blob_name)
                    blob.download_to_filename(str(local_path))
                    local_paths.append(local_path)
                    downloaded += 1
                
                # Progress indicator
                total_processed = downloaded + cached
                if total_processed % 10 == 0 or total_processed == len(image_names):
                    print(f"   Progress: {total_processed}/{len(image_names)} "
                          f"(Downloaded: {downloaded}, Cached: {cached})")
            
            print(f"✅ Download complete!")
            print(f"   Total: {len(local_paths)} images")
            print(f"   Downloaded: {downloaded}")
            print(f"   From cache: {cached}")
            print(f"   Location: {self.cache_dir}/\n")
            
            return local_paths
            
        except Exception as e:
            print(f"❌ Error downloading images: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_image_url(self, blob_name: str, expiration_minutes: int = 60) -> Optional[str]:
        """
        Generate a signed URL for an image (public access for limited time)
        
        Args:
            blob_name: Name of the blob in GCS
            expiration_minutes: URL expiration time in minutes
            
        Returns:
            Signed URL or None if failed
        """
        if not self.use_gcs:
            return None
        
        try:
            blob = self.bucket.blob(blob_name)
            url = blob.generate_signed_url(
                version="v4",
                expiration=expiration_minutes * 60,
                method="GET"
            )
            return url
            
        except Exception as e:
            print(f"❌ Error generating signed URL for {blob_name}: {e}")
            return None
    
    def upload_file(self, local_path: Path, blob_name: str) -> bool:
        """
        Upload a file to GCS bucket
        
        Args:
            local_path: Local file path
            blob_name: Destination blob name in GCS
            
        Returns:
            True if successful, False otherwise
        """
        if not self.use_gcs:
            return False
        
        try:
            blob = self.bucket.blob(blob_name)
            blob.upload_from_filename(str(local_path))
            print(f"✅ Uploaded {local_path.name} to GCS: {blob_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error uploading {local_path}: {e}")
            return False
    
    def clear_cache(self, prefix: str = "") -> int:
        """
        Clear local cache directory
        
        Args:
            prefix: Only clear files with this prefix
            
        Returns:
            Number of files deleted
        """
        if not self.cache_dir.exists():
            return 0
        
        deleted = 0
        for file_path in self.cache_dir.rglob("*"):
            if file_path.is_file():
                if not prefix or str(file_path).startswith(str(self.cache_dir / prefix)):
                    file_path.unlink()
                    deleted += 1
        
        print(f"🗑️  Cleared {deleted} cached files")
        return deleted
    
    def get_local_or_gcs_path(self, image_name: str, local_dir: str = "a_test") -> Path:
        """
        Get image path - either from local storage or download from GCS
        
        Args:
            image_name: Name of the image file
            local_dir: Local directory to check first
            
        Returns:
            Path to the image file
        """
        # Try local first
        local_path = Path(local_dir) / image_name
        if local_path.exists():
            return local_path
        
        # If using GCS, download
        if self.use_gcs:
            # Try with prefix
            blob_name = f"{local_dir}/{image_name}"
            downloaded_path = self.download_image(blob_name)
            if downloaded_path:
                return downloaded_path
            
            # Try without prefix (direct in bucket root)
            downloaded_path = self.download_image(image_name)
            if downloaded_path:
                return downloaded_path
        
        # Return local path even if not exists (for error handling)
        return local_path


# Singleton instance
_gcs_manager = None

def get_gcs_manager() -> GCSStorageManager:
    """Get or create GCS storage manager singleton"""
    global _gcs_manager
    if _gcs_manager is None:
        _gcs_manager = GCSStorageManager()
    return _gcs_manager


if __name__ == "__main__":
    """Test GCS connection"""
    print("Testing GCS Storage Manager...\n")
    
    manager = GCSStorageManager()
    
    if manager.use_gcs:
        # List images
        images = manager.list_images(prefix="test/")
        print(f"\nFound {len(images)} images")
        
        # Download all images
        if images:
            local_paths = manager.download_all_images(prefix="test/")
            print(f"\nDownloaded {len(local_paths)} images to local cache")
    else:
        print("GCS not enabled. Set USE_GCS_STORAGE=true in .env")
