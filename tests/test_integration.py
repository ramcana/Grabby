#!/usr/bin/env python3
"""
Comprehensive integration tests for Grabby video downloader.
Tests all major components and interfaces.
"""

import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests
from fastapi.testclient import TestClient

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.api.fastapi_app import app
from backend.core.unified_downloader import create_downloader
from backend.core.queue_manager import QueueManager
from backend.core.event_bus import EventBus
from backend.core.rules_engine import RulesEngine
from config.profile_manager import ProfileManager


class TestGrabbyIntegration:
    """Integration tests for the complete Grabby system."""
    
    @pytest.fixture
    def client(self):
        """FastAPI test client."""
        return TestClient(app)
    
    @pytest.fixture
    def temp_dir(self):
        """Temporary directory for test downloads."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def mock_downloader(self):
        """Mock downloader for testing without actual downloads."""
        with patch('yt_dlp.YoutubeDL') as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            mock_instance.extract_info.return_value = {
                'title': 'Test Video',
                'duration': 120,
                'uploader': 'Test Channel',
                'view_count': 1000,
                'formats': [{'format_id': 'best', 'ext': 'mp4'}]
            }
            yield mock_instance
    
    def test_api_health_check(self, client):
        """Test API health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_video_info_extraction(self, client, mock_downloader):
        """Test video info extraction via API."""
        test_url = "https://www.youtube.com/watch?v=test"
        response = client.post("/video-info", json={"url": test_url})
        
        assert response.status_code == 200
        data = response.json()
        assert "title" in data
        assert "duration" in data
    
    def test_download_submission(self, client, temp_dir, mock_downloader):
        """Test download submission and tracking."""
        test_url = "https://www.youtube.com/watch?v=test"
        
        response = client.post("/download", json={
            "urls": [test_url],
            "quality": "720p",
            "output_path": temp_dir
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "download_id" in data
        
        # Check download status
        download_id = data["download_id"]
        status_response = client.get(f"/downloads/{download_id}")
        assert status_response.status_code == 200
    
    def test_queue_management(self, temp_dir):
        """Test queue manager functionality."""
        queue_manager = QueueManager()
        
        # Add items to queue
        item1 = queue_manager.add_to_queue(
            "https://www.youtube.com/watch?v=test1",
            output_path=temp_dir,
            priority=1
        )
        item2 = queue_manager.add_to_queue(
            "https://www.youtube.com/watch?v=test2",
            output_path=temp_dir,
            priority=2
        )
        
        assert len(queue_manager.get_queue()) == 2
        
        # Test priority ordering
        queue = queue_manager.get_queue()
        assert queue[0]["priority"] >= queue[1]["priority"]
        
        # Test queue operations
        queue_manager.pause_item(item1)
        queue_manager.resume_item(item1)
        queue_manager.remove_from_queue(item2)
        
        assert len(queue_manager.get_queue()) == 1
    
    def test_event_bus_system(self):
        """Test event bus functionality."""
        event_bus = EventBus()
        events_received = []
        
        def test_handler(event):
            events_received.append(event)
        
        # Subscribe to events
        event_bus.subscribe("download.started", test_handler)
        
        # Emit event
        event_bus.emit("download.started", {
            "download_id": "test123",
            "url": "https://example.com/video"
        })
        
        # Wait for async processing
        time.sleep(0.1)
        
        assert len(events_received) == 1
        assert events_received[0].event_type == "download.started"
    
    def test_profile_management(self, temp_dir):
        """Test download profile system."""
        profile_manager = ProfileManager()
        
        # Test loading default profiles
        profiles = profile_manager.list_profiles()
        assert "default" in profiles
        assert "audio_only" in profiles
        
        # Test profile creation
        custom_profile = {
            "name": "test_profile",
            "quality": "1080p",
            "format": "mp4",
            "extract_audio": False,
            "output_template": "%(title)s.%(ext)s"
        }
        
        profile_path = Path(temp_dir) / "test_profile.yaml"
        profile_manager.create_profile("test_profile", custom_profile, str(profile_path))
        
        # Test profile loading
        loaded_profile = profile_manager.load_profile("test_profile")
        assert loaded_profile.quality == "1080p"
    
    def test_rules_engine(self, temp_dir):
        """Test smart rules engine functionality."""
        rules_engine = RulesEngine()
        
        # Create test rule
        test_rule = {
            "name": "Test Rule",
            "enabled": True,
            "priority": 1,
            "conditions": [
                {
                    "type": "url_pattern",
                    "operator": "contains",
                    "value": "youtube.com"
                }
            ],
            "actions": [
                {
                    "type": "set_priority",
                    "value": 5
                }
            ]
        }
        
        rules_engine.add_rule(test_rule)
        
        # Test rule evaluation
        download_info = {
            "url": "https://www.youtube.com/watch?v=test",
            "title": "Test Video",
            "priority": 1
        }
        
        result = rules_engine.evaluate_rules(download_info)
        assert result["priority"] == 5  # Should be modified by rule
    
    @pytest.mark.asyncio
    async def test_unified_downloader(self, temp_dir, mock_downloader):
        """Test unified downloader interface."""
        downloader = create_downloader(
            mode="legacy",
            output_path=temp_dir
        )
        
        # Test download info extraction
        info = await downloader.get_video_info("https://www.youtube.com/watch?v=test")
        assert "title" in info
        
        # Test download initiation
        download_id = await downloader.download(
            "https://www.youtube.com/watch?v=test",
            quality="720p"
        )
        assert download_id is not None
    
    def test_api_endpoints_comprehensive(self, client):
        """Test all major API endpoints."""
        # Test stats endpoint
        response = client.get("/stats")
        assert response.status_code == 200
        
        # Test queue endpoint
        response = client.get("/queue")
        assert response.status_code == 200
        
        # Test downloads endpoint
        response = client.get("/downloads")
        assert response.status_code == 200
        
        # Test profiles endpoint
        response = client.get("/profiles")
        assert response.status_code == 200
        
        # Test settings endpoint
        response = client.get("/settings")
        assert response.status_code == 200
    
    def test_websocket_connection(self, client):
        """Test WebSocket connection for real-time updates."""
        with client.websocket_connect("/ws") as websocket:
            # Send test message
            websocket.send_json({"type": "ping"})
            
            # Receive response
            data = websocket.receive_json()
            assert data["type"] == "pong"
    
    def test_error_handling(self, client):
        """Test error handling across the system."""
        # Test invalid URL
        response = client.post("/video-info", json={"url": "invalid-url"})
        assert response.status_code == 400
        
        # Test non-existent download
        response = client.get("/downloads/non-existent")
        assert response.status_code == 404
        
        # Test invalid download request
        response = client.post("/download", json={
            "urls": [],  # Empty URLs
            "quality": "invalid"
        })
        assert response.status_code == 400


class TestCLIInterface:
    """Test CLI interface functionality."""
    
    def test_cli_help(self):
        """Test CLI help command."""
        import subprocess
        result = subprocess.run([
            sys.executable, "-m", "cli.main", "--help"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        assert "download" in result.stdout
    
    def test_cli_info_command(self, mock_downloader):
        """Test CLI info extraction."""
        import subprocess
        with patch('yt_dlp.YoutubeDL'):
            result = subprocess.run([
                sys.executable, "-m", "cli.main", "info",
                "https://www.youtube.com/watch?v=test"
            ], capture_output=True, text=True)
            
            # Should not crash (return code 0 or 1 depending on mock)
            assert result.returncode in [0, 1]


def run_integration_tests():
    """Run all integration tests."""
    print("🧪 Running Grabby Integration Tests...")
    
    # Run pytest
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short"
    ])
    
    if exit_code == 0:
        print("✅ All integration tests passed!")
    else:
        print("❌ Some tests failed. Check output above.")
    
    return exit_code


if __name__ == "__main__":
    run_integration_tests()
