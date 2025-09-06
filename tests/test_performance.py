#!/usr/bin/env python3
"""
Performance benchmarks and load tests for Grabby video downloader.
"""

import asyncio
import time
import concurrent.futures
import psutil
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.unified_downloader import create_downloader
from backend.core.queue_manager import QueueManager
from backend.core.event_bus import EventBus
from backend.core.rules_engine import RulesEngine


class PerformanceBenchmarks:
    """Performance benchmarks for Grabby components."""
    
    def __init__(self):
        self.results = {}
    
    def measure_time(self, func_name):
        """Decorator to measure execution time."""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                result = func(*args, **kwargs)
                end_time = time.time()
                
                execution_time = end_time - start_time
                self.results[func_name] = {
                    'execution_time': execution_time,
                    'timestamp': time.time()
                }
                print(f"⏱️  {func_name}: {execution_time:.3f}s")
                return result
            return wrapper
        return decorator
    
    @measure_time("queue_manager_bulk_operations")
    def test_queue_manager_performance(self, num_items=1000):
        """Test queue manager with bulk operations."""
        queue_manager = QueueManager()
        
        # Bulk add items
        start_time = time.time()
        for i in range(num_items):
            queue_manager.add_to_queue(
                f"https://example.com/video{i}",
                priority=i % 10,
                output_path="/tmp"
            )
        add_time = time.time() - start_time
        
        # Bulk retrieve
        start_time = time.time()
        queue = queue_manager.get_queue()
        retrieve_time = time.time() - start_time
        
        # Bulk operations
        start_time = time.time()
        for item in queue[:100]:  # Operate on first 100
            queue_manager.pause_item(item['id'])
            queue_manager.resume_item(item['id'])
        operations_time = time.time() - start_time
        
        print(f"   📊 Added {num_items} items in {add_time:.3f}s")
        print(f"   📊 Retrieved queue in {retrieve_time:.3f}s")
        print(f"   📊 100 pause/resume operations in {operations_time:.3f}s")
        
        return {
            'add_time': add_time,
            'retrieve_time': retrieve_time,
            'operations_time': operations_time,
            'items_per_second': num_items / add_time
        }
    
    @measure_time("event_bus_throughput")
    def test_event_bus_performance(self, num_events=10000):
        """Test event bus throughput."""
        event_bus = EventBus()
        events_processed = 0
        
        def event_handler(event):
            nonlocal events_processed
            events_processed += 1
        
        # Subscribe to events
        event_bus.subscribe("performance.test", event_handler)
        
        # Emit events rapidly
        start_time = time.time()
        for i in range(num_events):
            event_bus.emit("performance.test", {"index": i})
        
        # Wait for processing
        time.sleep(1)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"   📊 Processed {events_processed}/{num_events} events")
        print(f"   📊 Events per second: {events_processed/processing_time:.0f}")
        
        return {
            'events_processed': events_processed,
            'events_per_second': events_processed / processing_time,
            'processing_time': processing_time
        }
    
    @measure_time("rules_engine_evaluation")
    def test_rules_engine_performance(self, num_rules=100, num_evaluations=1000):
        """Test rules engine evaluation performance."""
        rules_engine = RulesEngine()
        
        # Create multiple rules
        for i in range(num_rules):
            rule = {
                "name": f"Rule {i}",
                "enabled": True,
                "priority": i,
                "conditions": [
                    {
                        "type": "url_pattern",
                        "operator": "contains",
                        "value": f"domain{i % 10}.com"
                    }
                ],
                "actions": [
                    {
                        "type": "set_priority",
                        "value": i % 10
                    }
                ]
            }
            rules_engine.add_rule(rule)
        
        # Test evaluation performance
        test_data = {
            "url": "https://domain5.com/video",
            "title": "Test Video",
            "priority": 1
        }
        
        start_time = time.time()
        for _ in range(num_evaluations):
            rules_engine.evaluate_rules(test_data.copy())
        end_time = time.time()
        
        evaluation_time = end_time - start_time
        evaluations_per_second = num_evaluations / evaluation_time
        
        print(f"   📊 {num_rules} rules, {num_evaluations} evaluations")
        print(f"   📊 Evaluations per second: {evaluations_per_second:.0f}")
        
        return {
            'num_rules': num_rules,
            'evaluations_per_second': evaluations_per_second,
            'evaluation_time': evaluation_time
        }
    
    @measure_time("concurrent_video_info_extraction")
    def test_concurrent_info_extraction(self, num_concurrent=50):
        """Test concurrent video info extraction."""
        with patch('yt_dlp.YoutubeDL') as mock_ytdl:
            # Mock the extractor
            mock_instance = MagicMock()
            mock_ytdl.return_value = mock_instance
            mock_instance.extract_info.return_value = {
                'title': 'Test Video',
                'duration': 120,
                'uploader': 'Test Channel'
            }
            
            async def extract_info(url):
                downloader = create_downloader(mode="legacy")
                return await downloader.get_video_info(url)
            
            async def run_concurrent_extractions():
                tasks = []
                for i in range(num_concurrent):
                    url = f"https://example.com/video{i}"
                    tasks.append(extract_info(url))
                
                start_time = time.time()
                results = await asyncio.gather(*tasks, return_exceptions=True)
                end_time = time.time()
                
                successful = sum(1 for r in results if not isinstance(r, Exception))
                total_time = end_time - start_time
                
                print(f"   📊 {successful}/{num_concurrent} successful extractions")
                print(f"   📊 Total time: {total_time:.3f}s")
                print(f"   📊 Extractions per second: {successful/total_time:.1f}")
                
                return {
                    'successful': successful,
                    'total_time': total_time,
                    'extractions_per_second': successful / total_time
                }
            
            return asyncio.run(run_concurrent_extractions())
    
    @measure_time("memory_usage_analysis")
    def test_memory_usage(self):
        """Analyze memory usage of core components."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create components
        queue_manager = QueueManager()
        event_bus = EventBus()
        rules_engine = RulesEngine()
        
        # Add data to components
        for i in range(1000):
            queue_manager.add_to_queue(f"https://example.com/video{i}")
            event_bus.emit("test.event", {"data": f"test{i}"})
        
        for i in range(50):
            rules_engine.add_rule({
                "name": f"Rule {i}",
                "enabled": True,
                "conditions": [{"type": "url_pattern", "value": f"test{i}"}],
                "actions": [{"type": "set_priority", "value": i}]
            })
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"   📊 Initial memory: {initial_memory:.1f} MB")
        print(f"   📊 Final memory: {final_memory:.1f} MB")
        print(f"   📊 Memory increase: {memory_increase:.1f} MB")
        
        return {
            'initial_memory_mb': initial_memory,
            'final_memory_mb': final_memory,
            'memory_increase_mb': memory_increase
        }
    
    def run_all_benchmarks(self):
        """Run all performance benchmarks."""
        print("🚀 Running Grabby Performance Benchmarks...")
        print("=" * 50)
        
        # Queue Manager Performance
        print("\n📋 Queue Manager Performance:")
        queue_results = self.test_queue_manager_performance()
        
        # Event Bus Performance
        print("\n📡 Event Bus Performance:")
        event_results = self.test_event_bus_performance()
        
        # Rules Engine Performance
        print("\n🤖 Rules Engine Performance:")
        rules_results = self.test_rules_engine_performance()
        
        # Concurrent Operations
        print("\n⚡ Concurrent Operations:")
        concurrent_results = self.test_concurrent_info_extraction()
        
        # Memory Usage
        print("\n💾 Memory Usage Analysis:")
        memory_results = self.test_memory_usage()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Performance Summary:")
        print(f"   Queue operations: {queue_results['items_per_second']:.0f} items/sec")
        print(f"   Event processing: {event_results['events_per_second']:.0f} events/sec")
        print(f"   Rule evaluations: {rules_results['evaluations_per_second']:.0f} eval/sec")
        print(f"   Concurrent extractions: {concurrent_results['extractions_per_second']:.1f} extract/sec")
        print(f"   Memory overhead: {memory_results['memory_increase_mb']:.1f} MB")
        
        return self.results


def run_performance_tests():
    """Run performance benchmarks."""
    benchmarks = PerformanceBenchmarks()
    results = benchmarks.run_all_benchmarks()
    
    # Save results to file
    import json
    results_file = Path(__file__).parent / "performance_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")
    return results


if __name__ == "__main__":
    run_performance_tests()
