#!/usr/bin/env python3
"""
Test script for multi-engine integration
Tests the unified downloader with different engines
"""
import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.core.unified_downloader import create_downloader
from backend.core.downloader import DownloadStatus

async def test_multi_engine_integration():
    """Test the multi-engine integration"""
    
    print("🧪 Testing Multi-Engine Integration")
    print("=" * 50)
    
    # Test URLs for different engines
    test_urls = {
        "YouTube": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "Instagram": "https://www.instagram.com/p/example/",
        "Reddit": "https://www.reddit.com/r/videos/comments/example/",
        "Twitch": "https://www.twitch.tv/videos/123456789"
    }
    
    # Create multi-engine downloader
    print("🔧 Creating multi-engine downloader...")
    downloader = create_downloader(
        use_multi_engine=True,
        output_path="./test_downloads",
        concurrent_downloads=2
    )
    
    try:
        await downloader.initialize()
        print("✅ Downloader initialized successfully")
        
        # Test engine status
        status = downloader.get_engine_status()
        print(f"\n📊 Engine Status:")
        print(f"  Available engines: {status.get('available_engines', [])}")
        print(f"  Multi-engine enabled: {status.get('multi_engine', True)}")
        
        # Test optimal engine selection
        print(f"\n🎯 Testing engine selection:")
        for platform, url in test_urls.items():
            try:
                optimal_engine = await downloader.get_optimal_engine(url)
                print(f"  {platform:12} → {optimal_engine}")
            except Exception as e:
                print(f"  {platform:12} → Error: {e}")
        
        # Test queue status
        queue_status = downloader.get_queue_status()
        print(f"\n📋 Queue Status:")
        print(f"  Total items: {queue_status.get('total_items', 0)}")
        print(f"  Pending: {queue_status.get('pending', 0)}")
        print(f"  Active: {queue_status.get('active', 0)}")
        
        print("\n✅ Multi-engine integration test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_legacy_mode():
    """Test legacy yt-dlp only mode"""
    
    print("\n🧪 Testing Legacy Mode (yt-dlp only)")
    print("=" * 50)
    
    # Create legacy downloader
    print("🔧 Creating legacy downloader...")
    downloader = create_downloader(
        use_multi_engine=False,
        output_path="./test_downloads"
    )
    
    try:
        await downloader.initialize()
        print("✅ Legacy downloader initialized successfully")
        
        # Test engine status
        status = downloader.get_engine_status()
        print(f"\n📊 Engine Status:")
        print(f"  Engines: {status.get('engines', [])}")
        print(f"  Multi-engine: {status.get('multi_engine', False)}")
        
        print("\n✅ Legacy mode test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Legacy test failed: {e}")

async def test_cli_integration():
    """Test CLI integration"""
    
    print("\n🧪 Testing CLI Integration")
    print("=" * 50)
    
    try:
        # Import CLI components
        from cli.main import download_urls
        from backend.core.downloader import DownloadOptions
        
        print("✅ CLI imports successful")
        
        # Test options creation
        options = DownloadOptions(
            output_path="./test_downloads",
            format_selector="best[height<=720]",
            concurrent_downloads=1
        )
        
        print("✅ CLI options created successfully")
        print(f"  Output path: {options.output_path}")
        print(f"  Format: {options.format_selector}")
        print(f"  Concurrent: {options.concurrent_downloads}")
        
    except Exception as e:
        print(f"❌ CLI integration test failed: {e}")

async def main():
    """Run all integration tests"""
    
    print("🚀 Starting Multi-Engine Integration Tests")
    print("=" * 60)
    
    await test_multi_engine_integration()
    await test_legacy_mode()
    await test_cli_integration()
    
    print("\n" + "=" * 60)
    print("🎉 All integration tests completed!")
    print("\nNext steps:")
    print("  • Test with real URLs using: python cli/main.py download --engine multi --show-engines <URL>")
    print("  • Check engine availability: python -c \"from multi_engine_downloader import *; print('Engines available')\"")
    print("  • Run full system test: python test_basic.py")

if __name__ == "__main__":
    asyncio.run(main())
