#!/usr/bin/env python3
"""
Comprehensive test runner for Grabby
Runs all test suites and provides detailed reporting
"""
import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def run_test_suite(test_name, test_module):
    """Run a test suite and capture results"""
    print(f"\n🧪 Running {test_name}")
    print("=" * 50)
    
    start_time = time.time()
    
    try:
        if hasattr(test_module, 'main'):
            if asyncio.iscoroutinefunction(test_module.main):
                asyncio.run(test_module.main())
            else:
                test_module.main()
        else:
            print("✅ Module imported successfully (no main function)")
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n✅ {test_name} completed in {duration:.2f}s")
        return True, duration
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n❌ {test_name} failed after {duration:.2f}s")
        print(f"Error: {e}")
        return False, duration

async def main():
    """Run all test suites"""
    print("🚀 Grabby Test Suite Runner")
    print("=" * 60)
    
    # Test suites to run
    test_suites = [
        ("Quick Tests", "test_quick"),
        ("Basic Functionality", "test_basic"),
        ("Multi-Engine Integration", "test_multi_engine_integration"),
        ("Integration Tests", "test_integration"),
        ("Performance Tests", "test_performance"),
    ]
    
    results = []
    total_start = time.time()
    
    for test_name, module_name in test_suites:
        try:
            # Import test module
            module = __import__(module_name)
            success, duration = run_test_suite(test_name, module)
            results.append((test_name, success, duration))
            
        except ImportError as e:
            print(f"\n⚠️ Could not import {module_name}: {e}")
            results.append((test_name, False, 0))
    
    total_end = time.time()
    total_duration = total_end - total_start
    
    # Summary
    print(f"\n📊 Test Summary")
    print("=" * 60)
    
    passed = 0
    failed = 0
    total_test_time = 0
    
    for test_name, success, duration in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name:25} ({duration:.2f}s)")
        
        if success:
            passed += 1
        else:
            failed += 1
        
        total_test_time += duration
    
    print(f"\n🎯 Results: {passed} passed, {failed} failed")
    print(f"⏱️ Total test time: {total_test_time:.2f}s")
    print(f"⏱️ Total runtime: {total_duration:.2f}s")
    
    if failed == 0:
        print("\n🎉 All tests passed! Grabby is ready for production.")
    else:
        print(f"\n⚠️ {failed} test suite(s) failed. Please review the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())