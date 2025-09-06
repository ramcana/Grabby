"""
REST API - Enables both web and desktop interfaces
"""
import json
import asyncio
import uuid
import os
import sys
import subprocess
import platform
import psutil
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.core.downloader import UniversalDownloader
from backend.core.models import DownloadOptions, DownloadProgress, DownloadStatus
from backend.core.unified_downloader import create_downloader
from config.profile_manager import ProfileManager, DownloadProfile

# Pydantic models for API
class DownloadRequest(BaseModel):
    urls: List[HttpUrl]
    output_path: Optional[str] = "./downloads"
    format_selector: Optional[str] = "best[height<=1080]"
    audio_format: Optional[str] = "best"
    extract_audio: Optional[bool] = False
    write_subtitles: Optional[bool] = False
    write_thumbnail: Optional[bool] = False
    concurrent_downloads: Optional[int] = 3
    profile: Optional[str] = None

class VideoInfoRequest(BaseModel):
    url: HttpUrl

class DownloadResponse(BaseModel):
    download_id: str
    status: str
    message: str

class ProgressResponse(BaseModel):
    url: str
    status: str
    progress_percent: float
    speed: str
    eta: str
    downloaded_bytes: int
    total_bytes: int
    filename: str
    error_message: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

class VideoInfoResponse(BaseModel):
    title: str
    uploader: str
    duration: Optional[int]
    view_count: Optional[int]
    upload_date: Optional[str]
    description: Optional[str]
    thumbnail: Optional[str]
    formats: List[Dict]

# Global state management
active_downloads: Dict[str, Dict] = {}
completed_downloads: Dict[str, Dict] = {}  # Persist completed downloads
websocket_connections: List[WebSocket] = []
download_speeds: List[float] = []  # Track recent download speeds
last_speed_update = datetime.now()

app = FastAPI(
    title="Grabby Video Downloader API",
    description="Universal video downloader with support for multiple platforms",
    version="1.0.0"
)

# Use FastAPI app directly (no Socket.IO wrapper)
socket_app = app

# CORS middleware for web interface
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.connections:
            return
            
        disconnected = []
        for connection in self.connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

websocket_manager = WebSocketManager()

# Removed Socket.IO handlers - using native WebSocket only

def progress_callback(download_id: str, progress: DownloadProgress):
    """Callback to handle download progress updates"""
    # Update active downloads
    if download_id in active_downloads:
        active_downloads[download_id]['progress'] = progress
    
    # Broadcast to WebSocket clients
    message = {
        "type": "progress_update",
        "download_id": download_id,
        "data": {
            "url": progress.url,
            "status": progress.status.value,
            "progress_percent": progress.progress_percent,
            "speed": progress.speed,
            "eta": progress.eta,
            "downloaded_bytes": progress.downloaded_bytes,
            "total_bytes": progress.total_bytes,
            "filename": progress.filename,
            "error_message": progress.error_message,
            "started_at": progress.started_at.isoformat() if progress.started_at else None,
            "completed_at": progress.completed_at.isoformat() if progress.completed_at else None
        }
    }
    
    # Use asyncio to broadcast (since this callback might be called from sync context)
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(websocket_manager.broadcast(message))
    except:
        pass  # No event loop available

@app.get("/")
async def root():
    """API health check"""
    return {
        "message": "Grabby Video Downloader API",
        "version": "1.0.0",
        "status": "running",
        "active_downloads": len(active_downloads)
    }

@app.post("/download", response_model=DownloadResponse)
async def start_download(request: DownloadRequest, background_tasks: BackgroundTasks):
    """Start a new download"""
    
    download_id = str(uuid.uuid4())
    
    # Configure download options
    options = DownloadOptions(
        output_path=request.output_path,
        format_selector=request.format_selector,
        audio_format=request.audio_format,
        extract_audio=request.extract_audio,
        write_subtitles=request.write_subtitles,
        write_thumbnail=request.write_thumbnail,
        concurrent_downloads=request.concurrent_downloads
    )
    
    # Store download info
    active_downloads[download_id] = {
        "id": download_id,
        "urls": [str(url) for url in request.urls],
        "options": options,
        "status": "pending",
        "created_at": datetime.now(),
        "progress": None
    }
    
    # Start download in background
    background_tasks.add_task(run_download, download_id, request.urls, options)
    
    return DownloadResponse(
        download_id=download_id,
        status="started",
        message=f"Download started for {len(request.urls)} URL(s)"
    )

async def run_download(download_id: str, urls: List[HttpUrl], options: DownloadOptions):
    """Run the actual download process"""
    try:
        # Update status
        active_downloads[download_id]["status"] = "downloading"
        
        # Create downloader with progress callback
        downloader = UniversalDownloader(options)
        downloader.add_progress_callback(lambda progress: progress_callback(download_id, progress))
        
        # Convert URLs to strings
        url_strings = [str(url) for url in urls]
        
        # Start download
        results = await downloader.download_batch(url_strings)
        
        # Update final status
        successful = [r for r in results if r.status == DownloadStatus.COMPLETED]
        failed = [r for r in results if r.status == DownloadStatus.FAILED]
        
        active_downloads[download_id]["status"] = "completed"
        active_downloads[download_id]["results"] = {
            "successful": len(successful),
            "failed": len(failed),
            "total": len(results)
        }
        active_downloads[download_id]["completed_at"] = datetime.now()
        
        # Store completed download for persistence
        completed_downloads[download_id] = active_downloads[download_id].copy()
        
        # Broadcast completion
        global download_speeds, last_speed_update
        if hasattr(results[0], 'speed') and results[0].speed:
            try:
                # Parse speed string (e.g., "1.2 MB/s" -> bytes per second)
                speed_str = results[0].speed.replace('/s', '').strip()
                if 'MB' in speed_str:
                    speed_val = float(speed_str.replace('MB', '').strip()) * 1024 * 1024
                elif 'KB' in speed_str:
                    speed_val = float(speed_str.replace('KB', '').strip()) * 1024
                elif 'B' in speed_str:
                    speed_val = float(speed_str.replace('B', '').strip())
                else:
                    speed_val = 0
                
                if speed_val > 0:
                    download_speeds.append(speed_val)
                    # Keep only recent speeds (last 50 entries)
                    if len(download_speeds) > 50:
                        download_speeds = download_speeds[-50:]
            except (ValueError, AttributeError):
                pass
        
        completion_message = {
            "type": "download_completed",
            "download_id": download_id,
            "results": active_downloads[download_id]["results"]
        }
        await websocket_manager.broadcast(completion_message)
        
    except Exception as e:
        active_downloads[download_id]["status"] = "failed"
        active_downloads[download_id]["error"] = str(e)
        active_downloads[download_id]["completed_at"] = datetime.now()
        
        # Broadcast error
        error_message = {
            "type": "download_failed",
            "download_id": download_id,
            "error": str(e)
        }
        await websocket_manager.broadcast(error_message)

@app.post("/video-info", response_model=VideoInfoResponse)
async def get_video_info(request: VideoInfoRequest):
    """Get video information without downloading"""
    try:
        downloader = UniversalDownloader()
        info = await downloader.get_video_info(str(request.url))
        
        return VideoInfoResponse(
            title=info.get('title', 'Unknown'),
            uploader=info.get('uploader', 'Unknown'),
            duration=info.get('duration'),
            view_count=info.get('view_count'),
            upload_date=info.get('upload_date'),
            description=info.get('description'),
            thumbnail=info.get('thumbnail'),
            formats=info.get('formats', [])
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract video info: {str(e)}")

@app.get("/downloads", response_model=List[Dict])
async def list_downloads():
    """List all downloads"""
    return list(active_downloads.values())

@app.get("/downloads/recent")
async def get_recent_downloads():
    """Get recent downloads"""
    # Return the 10 most recent downloads
    recent = sorted(
        active_downloads.values(),
        key=lambda x: x.get("created_at", datetime.min),
        reverse=True
    )[:10]
    
    return {"items": recent}

@app.get("/downloads/{download_id}")
async def get_download(download_id: str):
    """Get specific download information"""
    if download_id not in active_downloads:
        raise HTTPException(status_code=404, detail="Download not found")
    
    return active_downloads[download_id]

@app.delete("/downloads/{download_id}")
async def cancel_download(download_id: str):
    """Cancel a download"""
    if download_id not in active_downloads:
        raise HTTPException(status_code=404, detail="Download not found")
    
    download_info = active_downloads[download_id]
    
    if download_info["status"] in ["completed", "failed", "cancelled"]:
        raise HTTPException(status_code=400, detail="Download cannot be cancelled")
    
    # Mark as cancelled
    active_downloads[download_id]["status"] = "cancelled"
    active_downloads[download_id]["completed_at"] = datetime.now()
    
    # Broadcast cancellation
    cancel_message = {
        "type": "download_cancelled",
        "download_id": download_id
    }
    await websocket_manager.broadcast(cancel_message)
    
    return {"message": "Download cancelled"}

@app.get("/downloads/{download_id}/progress", response_model=ProgressResponse)
async def get_download_progress(download_id: str):
    """Get download progress"""
    if download_id not in active_downloads:
        raise HTTPException(status_code=404, detail="Download not found")
    
    download_info = active_downloads[download_id]
    progress = download_info.get("progress")
    
    if not progress:
        # Return empty progress if not started yet
        return ProgressResponse(
            url="",
            status="pending",
            progress_percent=0.0,
            speed="0 B/s",
            eta="Unknown",
            downloaded_bytes=0,
            total_bytes=0,
            filename="",
            error_message="",
            started_at=None,
            completed_at=None
        )
    
    return ProgressResponse(
        url=progress.url,
        status=progress.status.value,
        progress_percent=progress.progress_percent,
        speed=progress.speed,
        eta=progress.eta,
        downloaded_bytes=progress.downloaded_bytes,
        total_bytes=progress.total_bytes,
        filename=progress.filename,
        error_message=progress.error_message,
        started_at=progress.started_at,
        completed_at=progress.completed_at
    )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket_manager.connect(websocket)
    
    try:
        # Send current downloads status
        await websocket.send_text(json.dumps({
            "type": "initial_state",
            "active_downloads": len(active_downloads)
        }))
        
        # Keep connection alive
        while True:
            await asyncio.sleep(1)  # Simple keep-alive without blocking receive
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)

# Health check endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_downloads": len(active_downloads)
    }

@app.get("/test")
async def test_endpoint():
    """Test endpoint to verify server is working"""
    return {"message": "Server is working", "timestamp": datetime.now().isoformat()}

@app.get("/queue")
async def get_queue():
    """Get download queue"""
    pending_downloads = [d for d in active_downloads.values() if d["status"] in ["pending", "downloading"]]
    
    stats = {
        "total": len(pending_downloads),
        "active": len([d for d in pending_downloads if d["status"] == "downloading"]),
        "pending": len([d for d in pending_downloads if d["status"] == "pending"]),
        "completed": len([d for d in active_downloads.values() if d["status"] == "completed"])
    }
    
    return {
        "items": pending_downloads,
        "stats": stats
    }

@app.get("/history")
async def get_history(limit: int = 50, offset: int = 0, search: Optional[str] = None):
    """Get download history"""
    completed_downloads = [d for d in active_downloads.values() if d["status"] in ["completed", "failed", "cancelled"]]
    
    # Filter by search if provided
    if search:
        completed_downloads = [
            d for d in completed_downloads 
            if search.lower() in str(d.get("urls", [])).lower()
        ]
    
    # Sort by completion time
    completed_downloads.sort(
        key=lambda x: x.get("completed_at", datetime.min),
        reverse=True
    )
    
    # Apply pagination
    total = len(completed_downloads)
    items = completed_downloads[offset:offset + limit]
    
    return {
        "items": items,
        "total": total,
        "offset": offset,
        "limit": limit
    }

@app.get("/settings")
async def get_settings():
    """Get application settings"""
    return {
        "download_path": "./downloads",
        "concurrent_downloads": 3,
        "auto_retry": True,
        "max_retries": 3,
        "notifications_enabled": True
    }

@app.put("/settings")
async def update_settings(settings: dict):
    """Update application settings"""
    # In a real app, this would save to database/config file
    return {"message": "Settings updated successfully", "settings": settings}

@app.get("/profiles")
async def get_profiles():
    """Get download profiles"""
    return {
        "profiles": [
            {"id": "default", "name": "Default", "format": "best[height<=1080]"},
            {"id": "high_quality", "name": "High Quality", "format": "best"},
            {"id": "audio_only", "name": "Audio Only", "format": "bestaudio"},
            {"id": "mobile", "name": "Mobile", "format": "best[height<=720]"}
        ]
    }

@app.post("/profiles")
async def create_profile(profile: dict):
    """Create a new download profile"""
    # In a real app, this would save to database
    return {"message": "Profile created successfully", "profile": profile}

@app.put("/profiles/{profile_id}")
async def update_profile(profile_id: str, profile: dict):
    """Update a download profile"""
    # In a real app, this would update in database
    return {"message": f"Profile {profile_id} updated successfully", "profile": profile}

@app.delete("/profiles/{profile_id}")
async def delete_profile(profile_id: str):
    """Delete a download profile"""
    # In a real app, this would delete from database
    return {"message": f"Profile {profile_id} deleted successfully"}

def get_system_stats():
    """Get real system statistics"""
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Disk usage for downloads directory
        downloads_path = "./downloads"
        if os.path.exists(downloads_path):
            disk_usage = shutil.disk_usage(downloads_path)
            total_gb = disk_usage.total / (1024**3)
            used_gb = (disk_usage.total - disk_usage.free) / (1024**3)
            disk_usage_str = f"{used_gb:.1f} GB"
        else:
            disk_usage_str = "0 GB"
        
        # Calculate average download speed from recent downloads
        global download_speeds, last_speed_update
        current_time = datetime.now()
        
        # Clean old speed entries (older than 5 minutes)
        cutoff_time = current_time - timedelta(minutes=5)
        download_speeds = [speed for speed in download_speeds if speed > 0]
        
        if download_speeds:
            avg_speed_bps = sum(download_speeds) / len(download_speeds)
            if avg_speed_bps > 1024**2:  # MB/s
                speed_str = f"{avg_speed_bps / (1024**2):.1f} MB/s"
            elif avg_speed_bps > 1024:  # KB/s
                speed_str = f"{avg_speed_bps / 1024:.1f} KB/s"
            else:
                speed_str = f"{avg_speed_bps:.0f} B/s"
        else:
            speed_str = "0 B/s"
        
        return {
            "cpu_usage": round(cpu_percent, 1),
            "memory_usage": round(memory_percent, 1),
            "download_speed": speed_str,
            "disk_usage": disk_usage_str
        }
    except Exception as e:
        # Fallback to safe defaults if psutil fails
        return {
            "cpu_usage": 0,
            "memory_usage": 0,
            "download_speed": "0 B/s",
            "disk_usage": "0 GB"
        }

@app.get("/stats")
async def get_stats():
    """Get system and download statistics"""
    total_downloads = len(active_downloads) + len(completed_downloads)
    active_count = len([d for d in active_downloads.values() if d["status"] == "downloading"])
    completed_count = len([d for d in active_downloads.values() if d["status"] == "completed"]) + len(completed_downloads)
    failed_count = len([d for d in active_downloads.values() if d["status"] == "failed"])
    
    # Get real system stats
    system_stats = get_system_stats()
    
    return {
        "total_downloads": total_downloads,
        "active_downloads": active_count,
        "completed_downloads": completed_count,
        "failed_downloads": failed_count,
        "websocket_connections": len(websocket_manager.connections),
        "completed_today": completed_count,  # Simplified for now
        **system_stats
    }

# File serving endpoints
@app.get("/downloads/{download_id}/file")
async def download_file(download_id: str):
    """Serve the downloaded file for direct download"""
    # Check both active and completed downloads
    download = None
    if download_id in active_downloads:
        download = active_downloads[download_id]
    elif download_id in completed_downloads:
        download = completed_downloads[download_id]
    else:
        raise HTTPException(status_code=404, detail="Download not found")
    
    # Try to get filename from multiple possible locations
    filename = None
    
    # Check if there's a progress object
    progress = download.get("progress")
    if progress:
        if hasattr(progress, 'filename'):
            filename = progress.filename
        elif isinstance(progress, dict):
            filename = progress.get("filename")
    
    # If no filename from progress, check direct download properties
    if not filename and "results" in download:
        # For completed downloads, try to construct filename from download path and URL
        options = download.get("options", {})
        output_path = options.get("output_path", "./downloads")
        urls = download.get("urls", [])
        if urls:
            # This is a fallback - we'll need to find the actual file
            import glob
            pattern = os.path.join(output_path, "*")
            files = glob.glob(pattern)
            if files:
                # Get the most recent file
                filename = max(files, key=os.path.getctime)
    
    if not filename or not os.path.exists(filename):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=filename,
        filename=os.path.basename(filename),
        media_type='application/octet-stream'
    )

@app.post("/downloads/{download_id}/open-folder")
async def open_folder(download_id: str):
    """Open the download folder in file explorer"""
    # Check both active and completed downloads
    download = None
    if download_id in active_downloads:
        download = active_downloads[download_id]
    elif download_id in completed_downloads:
        download = completed_downloads[download_id]
    else:
        raise HTTPException(status_code=404, detail="Download not found")
    
    # Try to get filename from multiple possible locations
    filename = None
    
    # Check if there's a progress object
    progress = download.get("progress")
    if progress:
        if hasattr(progress, 'filename'):
            filename = progress.filename
        elif isinstance(progress, dict):
            filename = progress.get("filename")
    
    # If no filename from progress, check direct download properties
    if not filename and "results" in download:
        # For completed downloads, try to construct filename from download path and URL
        options = download.get("options", {})
        output_path = options.get("output_path", "./downloads")
        urls = download.get("urls", [])
        if urls:
            # This is a fallback - we'll need to find the actual file
            import glob
            pattern = os.path.join(output_path, "*")
            files = glob.glob(pattern)
            if files:
                # Get the most recent file
                filename = max(files, key=os.path.getctime)
    
    # If still no filename, use default download folder
    if not filename:
        options = download.get("options", {})
        folder_path = options.get("output_path", "./downloads")
    else:
        folder_path = os.path.dirname(filename)
    
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail="Folder not found")
    
    try:
        # Open folder based on OS
        system = platform.system()
        if system == "Windows":
            os.startfile(folder_path)
        elif system == "Darwin":  # macOS
            subprocess.run(["open", folder_path])
        else:  # Linux
            subprocess.run(["xdg-open", folder_path])
        
        return {"message": "Folder opened successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to open folder: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(socket_app, host="0.0.0.0", port=8000, reload=True)
