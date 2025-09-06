#!/usr/bin/env python3
"""
Quick test to verify Grabby functionality
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("🎬 Grabby Video Downloader - Quick Test")
print("=" * 50)

# Test 1: Import core modules
try:
    from backend.core.downloader import UniversalDownloader, DownloadOptions
    print("✅ Core downloader imported")
except ImportError as e:
    print(f"❌ Core downloader import failed: {e}")

# Test 2: Import CLI
try:
    from cli.main import cli
    print("✅ CLI module imported")
except ImportError as e:
    print(f"❌ CLI import failed: {e}")

# Test 3: Import API
try:
    from backend.api.fastapi_app import app
    print("✅ API module imported")
except ImportError as e:
    print(f"❌ API import failed: {e}")

# Test 4: Create downloader instance
try:
    options = DownloadOptions(output_path="./test")
    downloader = UniversalDownloader(options)
    print("✅ Downloader instance created")
except Exception as e:
    print(f"❌ Downloader creation failed: {e}")

print("\n🚀 Ready to use! Try these commands:")
print("  python main.py --help")
print("  python main.py info 'https://youtube.com/watch?v=dQw4w9WgXcQ'")
print("  python backend/api/fastapi_app.py")
