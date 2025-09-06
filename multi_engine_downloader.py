#!/usr/bin/env python3
"""
Multi-Engine Download Manager
Integrates yt-dlp+aria2c, streamlink, gallery-dl, and ripme
"""

import asyncio
import subprocess
import json
import re
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path
import aiohttp
import tempfile


class EngineType(Enum):
    YT_DLP_ARIA2 = "yt-dlp+aria2c"
    STREAMLINK = "streamlink"
    GALLERY_DL = "gallery-dl"
    RIPME = "ripme"
    AUTO = "auto"


@dataclass
class DownloadRequest:
    url: str
    output_dir: Path = Path("./downloads")
    quality: str = "best"
    engine: EngineType = EngineType.AUTO
    options: Dict[str, Any] = field(default_factory=dict)
    progress_callback: Optional[Callable] = None
    completion_callback: Optional[Callable] = None


class DownloadEngine(ABC):
    """Base class for all download engines"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.is_available = self.check_availability()
    
    @abstractmethod
    async def download(self, request: DownloadRequest) -> Dict[str, Any]:
        """Download content and return result info"""
        pass
    
    @abstractmethod
    def check_availability(self) -> bool:
        """Check if engine binaries are available"""
        pass
    
    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Check if engine can handle this URL"""
        pass


class YtDlpAria2Engine(DownloadEngine):
    """yt-dlp with aria2c for segmented downloads"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.aria2_config = {
            'max-concurrent-downloads': 5,
            'max-connection-per-server': 16,
            'split': 16,
            'min-split-size': '1M',
            'continue': True,
            'max-tries': 5,
            'retry-wait': 3
        }
        self.aria2_config.update(self.config.get('aria2', {}))
    
    def check_availability(self) -> bool:
        try:
            subprocess.run(['yt-dlp', '--version'], 
                         capture_output=True, check=True)
            subprocess.run(['aria2c', '--version'], 
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def can_handle(self, url: str) -> bool:
        # yt-dlp handles most video sites
        video_patterns = [
            r'youtube\.com|youtu\.be',
            r'vimeo\.com',
            r'dailymotion\.com',
            r'twitch\.tv',
            r'facebook\.com',
            r'tiktok\.com',
            r'twitter\.com|x\.com'
        ]
        return any(re.search(pattern, url, re.I) for pattern in video_patterns)
    
    async def download(self, request: DownloadRequest) -> Dict[str, Any]:
        # First, extract download URLs with yt-dlp
        extract_cmd = [
            'yt-dlp',
            '--dump-json',
            '--no-download',
            f'--format={request.quality}',
            request.url
        ]
        
        try:
            result = await self._run_command(extract_cmd)
            video_info = json.loads(result.stdout)
            
            # Get the direct URL
            direct_url = video_info.get('url')
            if not direct_url:
                raise Exception("Could not extract direct URL")
            
            # Create aria2c input file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                filename = self._sanitize_filename(video_info.get('title', 'video'))
                ext = video_info.get('ext', 'mp4')
                output_path = request.output_dir / f"{filename}.{ext}"
                
                f.write(f"{direct_url}\n")
                f.write(f"  out={output_path.name}\n")
                f.write(f"  dir={request.output_dir}\n")
                
                # Add aria2c options
                for key, value in self.aria2_config.items():
                    f.write(f"  {key}={value}\n")
                
                input_file = f.name
            
            # Download with aria2c
            aria2_cmd = [
                'aria2c',
                '--input-file', input_file,
                '--summary-interval', '1'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *aria2_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Monitor progress
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                
                line = line.decode().strip()
                if request.progress_callback and 'ETA:' in line:
                    # Parse aria2c progress line
                    progress = self._parse_aria2_progress(line)
                    if progress:
                        await request.progress_callback(progress)
            
            await process.wait()
            
            # Clean up temp file
            Path(input_file).unlink(missing_ok=True)
            
            return {
                'status': 'success',
                'output_path': output_path,
                'title': video_info.get('title'),
                'duration': video_info.get('duration'),
                'engine': 'yt-dlp+aria2c'
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e), 'engine': 'yt-dlp+aria2c'}
    
    def _parse_aria2_progress(self, line: str) -> Optional[Dict[str, Any]]:
        # Parse aria2c progress line format
        # Example: [#1 SIZE:12.3MiB/45.6MiB(27%) CN:8 DL:1.2MiB ETA:30s]
        pattern = r'SIZE:([0-9.]+[KMGT]?iB)/([0-9.]+[KMGT]?iB)\((\d+)%\).*DL:([0-9.]+[KMGT]?iB).*ETA:(\w+)'
        match = re.search(pattern, line)
        if match:
            return {
                'downloaded': match.group(1),
                'total': match.group(2),
                'percentage': int(match.group(3)),
                'speed': match.group(4),
                'eta': match.group(5)
            }
        return None
    
    def _sanitize_filename(self, filename: str) -> str:
        # Remove invalid characters for filenames
        return re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    async def _run_command(self, cmd: List[str]) -> subprocess.CompletedProcess:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return subprocess.CompletedProcess(
            cmd, process.returncode, stdout, stderr
        )


class StreamlinkEngine(DownloadEngine):
    """Streamlink for live streams"""
    
    def check_availability(self) -> bool:
        try:
            subprocess.run(['streamlink', '--version'], 
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def can_handle(self, url: str) -> bool:
        # Streamlink handles live streaming platforms
        streaming_patterns = [
            r'twitch\.tv',
            r'youtube\.com/watch.*[?&]v=.*live',
            r'kick\.com',
            r'afreecatv\.com',
            r'douyu\.com',
            r'huya\.com'
        ]
        return any(re.search(pattern, url, re.I) for pattern in streaming_patterns)
    
    async def download(self, request: DownloadRequest) -> Dict[str, Any]:
        output_template = request.output_dir / f"stream_{int(asyncio.get_event_loop().time())}.ts"
        
        cmd = [
            'streamlink',
            request.url,
            request.quality,
            '--output', str(output_template),
            '--hls-live-restart',
            '--retry-streams', '5',
            '--retry-max', '10'
        ]
        
        # Add custom options
        if 'duration' in request.options:
            cmd.extend(['--hls-duration', str(request.options['duration'])])
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Monitor output for progress
            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                
                line = line.decode().strip()
                if request.progress_callback and 'Written' in line:
                    # Parse streamlink progress
                    progress = self._parse_streamlink_progress(line)
                    if progress:
                        await request.progress_callback(progress)
            
            await process.wait()
            
            return {
                'status': 'success',
                'output_path': output_template,
                'engine': 'streamlink'
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e), 'engine': 'streamlink'}
    
    def _parse_streamlink_progress(self, line: str) -> Optional[Dict[str, Any]]:
        # Parse streamlink output
        if 'Written' in line and 'bytes' in line:
            return {'status': 'recording', 'message': line}
        return None


class GalleryDlEngine(DownloadEngine):
    """gallery-dl for social media and image galleries"""
    
    def check_availability(self) -> bool:
        try:
            subprocess.run(['gallery-dl', '--version'], 
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def can_handle(self, url: str) -> bool:
        # gallery-dl specializes in image galleries and social media
        gallery_patterns = [
            r'instagram\.com',
            r'reddit\.com',
            r'twitter\.com|x\.com',
            r'pinterest\.com',
            r'tumblr\.com',
            r'pixiv\.net',
            r'deviantart\.com',
            r'artstation\.com'
        ]
        return any(re.search(pattern, url, re.I) for pattern in gallery_patterns)
    
    async def download(self, request: DownloadRequest) -> Dict[str, Any]:
        cmd = [
            'gallery-dl',
            '--dest', str(request.output_dir),
            '--write-metadata',
            '--write-info-json'
        ]
        
        # Add quality options
        if request.quality != 'best':
            cmd.extend(['--option', f'image-range=:{request.quality}'])
        
        # Custom options
        if 'archive' in request.options:
            cmd.extend(['--download-archive', request.options['archive']])
        
        cmd.append(request.url)
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            downloaded_files = []
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                
                line = line.decode().strip()
                if request.progress_callback:
                    await request.progress_callback({'message': line})
                
                # Track downloaded files
                if line.startswith('/') or line.startswith('C:'):
                    downloaded_files.append(line)
            
            await process.wait()
            
            return {
                'status': 'success',
                'downloaded_files': downloaded_files,
                'count': len(downloaded_files),
                'engine': 'gallery-dl'
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e), 'engine': 'gallery-dl'}


class RipmeEngine(DownloadEngine):
    """RipMe for image galleries (Java-based)"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.jar_path = self.config.get('jar_path', 'ripme.jar')
    
    def check_availability(self) -> bool:
        try:
            subprocess.run(['java', '-version'], 
                         capture_output=True, check=True)
            return Path(self.jar_path).exists()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def can_handle(self, url: str) -> bool:
        # RipMe handles various image hosting sites
        ripme_patterns = [
            r'imgur\.com',
            r'8muses\.com',
            r'motherless\.com',
            r'xhamster\.com',
            r'imagefap\.com'
        ]
        return any(re.search(pattern, url, re.I) for pattern in ripme_patterns)
    
    async def download(self, request: DownloadRequest) -> Dict[str, Any]:
        cmd = [
            'java', '-jar', self.jar_path,
            '--url', request.url,
            '--ripsdirectory', str(request.output_dir)
        ]
        
        if 'no_prop_file' in request.options:
            cmd.append('--no-prop-file')
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                
                line = line.decode().strip()
                if request.progress_callback and ('Downloaded' in line or 'Downloading' in line):
                    await request.progress_callback({'message': line})
            
            await process.wait()
            
            return {
                'status': 'success',
                'engine': 'ripme'
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e), 'engine': 'ripme'}


class MultiEngineDownloader:
    """Main coordinator that routes downloads to appropriate engines"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Initialize all engines
        self.engines = {
            EngineType.YT_DLP_ARIA2: YtDlpAria2Engine(config.get('yt-dlp-aria2')),
            EngineType.STREAMLINK: StreamlinkEngine(config.get('streamlink')),
            EngineType.GALLERY_DL: GalleryDlEngine(config.get('gallery-dl')),
            EngineType.RIPME: RipmeEngine(config.get('ripme'))
        }
        
        # Check which engines are available
        self.available_engines = {
            engine_type: engine for engine_type, engine in self.engines.items()
            if engine.is_available
        }
        
        print(f"Available engines: {list(self.available_engines.keys())}")
    
    def select_engine(self, url: str, preferred: EngineType = EngineType.AUTO) -> Optional[DownloadEngine]:
        """Select the best engine for a given URL"""
        
        if preferred != EngineType.AUTO and preferred in self.available_engines:
            engine = self.available_engines[preferred]
            if engine.can_handle(url):
                return engine
        
        # Auto-select best engine
        # Priority order: specialized tools first, then general purpose
        priority_order = [
            EngineType.STREAMLINK,    # Live streams
            EngineType.GALLERY_DL,    # Social media/galleries
            EngineType.RIPME,         # Image galleries
            EngineType.YT_DLP_ARIA2   # General video (fallback)
        ]
        
        for engine_type in priority_order:
            if engine_type in self.available_engines:
                engine = self.available_engines[engine_type]
                if engine.can_handle(url):
                    return engine
        
        return None
    
    async def download(self, request: DownloadRequest) -> Dict[str, Any]:
        """Download using the most appropriate engine"""
        
        engine = self.select_engine(request.url, request.engine)
        if not engine:
            return {
                'status': 'error',
                'message': f'No suitable engine found for URL: {request.url}',
                'available_engines': list(self.available_engines.keys())
            }
        
        print(f"Using engine: {engine.__class__.__name__}")
        
        # Ensure output directory exists
        request.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Perform download
        result = await engine.download(request)
        
        # Call completion callback if provided
        if request.completion_callback:
            await request.completion_callback(result)
        
        return result
    
    async def batch_download(self, requests: List[DownloadRequest]) -> List[Dict[str, Any]]:
        """Download multiple URLs concurrently"""
        
        # Group requests by engine type for optimal processing
        engine_groups = {}
        for req in requests:
            engine = self.select_engine(req.url, req.engine)
            if engine:
                engine_type = type(engine).__name__
                if engine_type not in engine_groups:
                    engine_groups[engine_type] = []
                engine_groups[engine_type].append(req)
        
        # Process each group with appropriate concurrency limits
        all_results = []
        for engine_type, reqs in engine_groups.items():
            # Limit concurrent downloads per engine
            semaphore = asyncio.Semaphore(self.config.get(f'{engine_type}_concurrent', 3))
            
            async def limited_download(request):
                async with semaphore:
                    return await self.download(request)
            
            tasks = [limited_download(req) for req in reqs]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            all_results.extend(results)
        
        return all_results


# Example usage and CLI interface
async def main():
    """Example usage of the multi-engine downloader"""
    
    config = {
        'yt-dlp-aria2': {
            'aria2': {
                'max-concurrent-downloads': 8,
                'max-connection-per-server': 16,
                'split': 16
            }
        },
        'ripme': {
            'jar_path': './ripme.jar'  # Path to RipMe jar file
        }
    }
    
    downloader = MultiEngineDownloader(config)
    
    # Progress callback
    async def progress_callback(progress):
        print(f"Progress: {progress}")
    
    # Completion callback  
    async def completion_callback(result):
        print(f"Completed: {result}")
    
    # Example downloads
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # yt-dlp+aria2c
        "https://www.twitch.tv/shroud",                  # streamlink (if live)
        "https://www.instagram.com/p/example/",          # gallery-dl
        "https://imgur.com/gallery/example"              # ripme
    ]
    
    requests = [
        DownloadRequest(
            url=url,
            output_dir=Path("./downloads"),
            quality="best",
            progress_callback=progress_callback,
            completion_callback=completion_callback
        )
        for url in test_urls
    ]
    
    # Batch download
    results = await downloader.batch_download(requests)
    
    for result in results:
        print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())