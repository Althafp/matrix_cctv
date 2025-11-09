"""
Cache Cleanup Utility
Clean up old GCS cached images
"""

import os
import time
from pathlib import Path
from datetime import datetime, timedelta


def get_cache_size(cache_dir="gcs_cache"):
    """Calculate total cache size"""
    total_size = 0
    for path in Path(cache_dir).rglob("*"):
        if path.is_file():
            total_size += path.stat().st_size
    return total_size


def get_file_age_hours(file_path):
    """Get file age in hours"""
    file_time = file_path.stat().st_mtime
    age_seconds = time.time() - file_time
    return age_seconds / 3600


def cleanup_old_files(cache_dir="gcs_cache", max_age_hours=1, dry_run=False):
    """
    Delete files older than specified hours
    
    Args:
        cache_dir: Cache directory path
        max_age_hours: Delete files older than this (default: 1 hour)
        dry_run: If True, only show what would be deleted
    """
    cache_path = Path(cache_dir)
    
    if not cache_path.exists():
        print(f"📁 Cache directory not found: {cache_dir}")
        return
    
    print(f"\n{'='*70}")
    print(f"🧹 CACHE CLEANUP UTILITY")
    print(f"{'='*70}")
    print(f"\n📂 Cache directory: {cache_dir}")
    print(f"⏰ Max age: {max_age_hours} hour(s)")
    print(f"🔍 Mode: {'DRY RUN (no actual deletion)' if dry_run else 'LIVE (will delete)'}")
    
    # Get all files
    all_files = [f for f in cache_path.rglob("*") if f.is_file()]
    
    if not all_files:
        print(f"\n✅ Cache is empty - nothing to clean!")
        return
    
    print(f"\n📊 Found {len(all_files)} cached files")
    
    # Calculate current cache size
    total_size = get_cache_size(cache_dir)
    print(f"💾 Current cache size: {total_size / (1024*1024):.2f} MB")
    
    # Find old files
    old_files = []
    for file_path in all_files:
        age_hours = get_file_age_hours(file_path)
        if age_hours > max_age_hours:
            old_files.append((file_path, age_hours))
    
    if not old_files:
        print(f"\n✅ No files older than {max_age_hours} hour(s) found!")
        print(f"💡 Cache is clean - all files are recent")
        return
    
    print(f"\n🗑️  Found {len(old_files)} files to delete:")
    
    # Calculate space to be freed
    space_to_free = sum(f[0].stat().st_size for f in old_files)
    print(f"💾 Space to free: {space_to_free / (1024*1024):.2f} MB")
    
    # Show sample files
    print(f"\n📋 Sample files to delete:")
    for file_path, age in old_files[:5]:
        print(f"   - {file_path.name} (age: {age:.1f} hours)")
    if len(old_files) > 5:
        print(f"   ... and {len(old_files) - 5} more")
    
    if dry_run:
        print(f"\n⚠️  DRY RUN MODE - No files were deleted")
        print(f"💡 Run without --dry-run to actually delete files")
        return
    
    # Confirm deletion
    print(f"\n⚠️  WARNING: This will permanently delete {len(old_files)} files!")
    confirm = input("❓ Continue? (yes/no): ").strip().lower()
    
    if confirm not in ['yes', 'y']:
        print("\n❌ Cleanup cancelled")
        return
    
    # Delete files
    print(f"\n🗑️  Deleting old files...")
    deleted = 0
    failed = 0
    
    for file_path, age in old_files:
        try:
            file_path.unlink()
            deleted += 1
        except Exception as e:
            print(f"   ❌ Failed to delete {file_path.name}: {e}")
            failed += 1
    
    # Clean up empty directories
    for dir_path in sorted(cache_path.rglob("*"), reverse=True):
        if dir_path.is_dir() and not list(dir_path.iterdir()):
            try:
                dir_path.rmdir()
            except:
                pass
    
    # Summary
    new_size = get_cache_size(cache_dir)
    freed = total_size - new_size
    
    print(f"\n{'='*70}")
    print(f"✅ CLEANUP COMPLETE!")
    print(f"{'='*70}")
    print(f"\n📊 Summary:")
    print(f"   ✅ Deleted: {deleted} files")
    if failed > 0:
        print(f"   ❌ Failed: {failed} files")
    print(f"   💾 Space freed: {freed / (1024*1024):.2f} MB")
    print(f"   📦 New cache size: {new_size / (1024*1024):.2f} MB")
    print(f"   📉 Reduction: {(freed/total_size*100):.1f}%")


def cleanup_all(cache_dir="gcs_cache"):
    """Delete entire cache directory"""
    cache_path = Path(cache_dir)
    
    if not cache_path.exists():
        print(f"📁 Cache directory not found: {cache_dir}")
        return
    
    # Calculate size before
    total_size = get_cache_size(cache_dir)
    file_count = len([f for f in cache_path.rglob("*") if f.is_file()])
    
    print(f"\n{'='*70}")
    print(f"🗑️  DELETE ENTIRE CACHE")
    print(f"{'='*70}")
    print(f"\n📂 Directory: {cache_dir}")
    print(f"📊 Files: {file_count}")
    print(f"💾 Size: {total_size / (1024*1024):.2f} MB")
    
    print(f"\n⚠️  WARNING: This will delete ALL cached files!")
    confirm = input("❓ Are you sure? (yes/no): ").strip().lower()
    
    if confirm not in ['yes', 'y']:
        print("\n❌ Deletion cancelled")
        return
    
    # Delete
    import shutil
    try:
        shutil.rmtree(cache_dir)
        print(f"\n✅ Cache deleted successfully!")
        print(f"💾 Freed {total_size / (1024*1024):.2f} MB")
    except Exception as e:
        print(f"\n❌ Error deleting cache: {e}")


def show_cache_info(cache_dir="gcs_cache"):
    """Show cache statistics"""
    cache_path = Path(cache_dir)
    
    if not cache_path.exists():
        print(f"\n📁 Cache directory not found: {cache_dir}")
        print(f"💡 Cache will be created when you analyze images")
        return
    
    print(f"\n{'='*70}")
    print(f"📊 CACHE INFORMATION")
    print(f"{'='*70}")
    
    all_files = [f for f in cache_path.rglob("*") if f.is_file()]
    
    if not all_files:
        print(f"\n📂 Cache directory: {cache_dir}")
        print(f"✅ Cache is empty")
        return
    
    # Calculate stats
    total_size = get_cache_size(cache_dir)
    
    # Categorize by age
    recent = []  # < 1 hour
    old = []     # > 1 hour
    
    for file_path in all_files:
        age = get_file_age_hours(file_path)
        if age < 1:
            recent.append((file_path, age))
        else:
            old.append((file_path, age))
    
    print(f"\n📂 Cache directory: {cache_dir}")
    print(f"📊 Total files: {len(all_files)}")
    print(f"💾 Total size: {total_size / (1024*1024):.2f} MB")
    
    print(f"\n⏰ File Age Distribution:")
    print(f"   🟢 Recent (< 1 hour): {len(recent)} files")
    print(f"   🔴 Old (> 1 hour): {len(old)} files")
    
    if old:
        old_size = sum(f[0].stat().st_size for f in old)
        print(f"\n💡 You can free {old_size / (1024*1024):.2f} MB by cleaning old files")
    
    # Show newest and oldest
    if all_files:
        all_with_age = [(f, get_file_age_hours(f)) for f in all_files]
        all_with_age.sort(key=lambda x: x[1])
        
        print(f"\n📋 Newest files:")
        for file_path, age in all_with_age[:3]:
            print(f"   - {file_path.name} ({age*60:.0f} minutes old)")
        
        if len(old) > 0:
            print(f"\n📋 Oldest files:")
            all_with_age.sort(key=lambda x: x[1], reverse=True)
            for file_path, age in all_with_age[:3]:
                print(f"   - {file_path.name} ({age:.1f} hours old)")


def main():
    """Main menu"""
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                  CACHE CLEANUP UTILITY                            ║
║            Manage GCS image cache storage                         ║
╚═══════════════════════════════════════════════════════════════════╝
""")
    
    print("Select an option:")
    print("  1. Show cache info")
    print("  2. Clean old files (> 1 hour)")
    print("  3. Clean old files (> 24 hours)")
    print("  4. Delete entire cache")
    print("  5. Dry run (see what would be deleted)")
    print("  6. Exit")
    
    choice = input("\nEnter choice (1-6): ").strip()
    
    if choice == '1':
        show_cache_info()
    elif choice == '2':
        cleanup_old_files(max_age_hours=1)
    elif choice == '3':
        cleanup_old_files(max_age_hours=24)
    elif choice == '4':
        cleanup_all()
    elif choice == '5':
        cleanup_old_files(max_age_hours=1, dry_run=True)
    elif choice == '6':
        print("\n👋 Goodbye!")
    else:
        print("\n❌ Invalid choice!")


if __name__ == "__main__":
    main()

