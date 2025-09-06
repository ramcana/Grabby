"""
Profile Manager for Grabby Video Downloader
Handles loading, validation, and management of download profiles
"""
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field, asdict
import yaml
import json
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class DownloadProfile:
    """Represents a download profile configuration"""
    name: str = "default"
    description: str = ""
    version: str = "1.0"
    
    # Output settings
    output_path: str = "./downloads"
    filename_template: str = "%(title)s.%(ext)s"
    create_subdirs: bool = False
    organize_by_uploader: bool = False
    
    # Quality settings
    video_format: str = "best[height<=1080]"
    audio_format: str = "best"
    prefer_free_codecs: bool = False
    max_filesize: Optional[str] = None
    
    # Download options
    concurrent_downloads: int = 3
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: int = 30
    rate_limit: Optional[str] = None
    
    # Post-processing
    extract_audio: bool = False
    write_subtitles: bool = False
    write_thumbnail: bool = True
    write_info_json: bool = False
    embed_metadata: bool = True
    convert_format: Optional[str] = None
    
    # Engine preferences
    preferred_engine: str = "auto"
    fallback_enabled: bool = True
    engine_specific: Dict[str, Any] = field(default_factory=dict)
    
    # Platform-specific overrides
    platform_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Filters and rules
    min_duration: Optional[int] = None
    max_duration: Optional[int] = None
    skip_live_streams: bool = False
    skip_premieres: bool = False
    allowed_extensions: List[str] = field(default_factory=list)
    blocked_uploaders: List[str] = field(default_factory=list)
    
    # Notifications
    notify_on_start: bool = False
    notify_on_complete: bool = True
    notify_on_error: bool = True
    notify_on_batch_complete: bool = True
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_builtin: bool = False
    
    @classmethod
    def from_yaml(cls, yaml_path: Path) -> 'DownloadProfile':
        """Load profile from YAML file"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return cls.from_dict(data, is_builtin=True)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], is_builtin: bool = False) -> 'DownloadProfile':
        """Create profile from dictionary"""
        profile = cls()
        
        # Basic info
        profile.name = data.get('name', 'unnamed')
        profile.description = data.get('description', '')
        profile.version = data.get('version', '1.0')
        profile.is_builtin = is_builtin
        
        # Output settings
        output = data.get('output', {})
        profile.output_path = output.get('path', './downloads')
        profile.filename_template = output.get('filename_template', '%(title)s.%(ext)s')
        profile.create_subdirs = output.get('create_subdirs', False)
        profile.organize_by_uploader = output.get('organize_by_uploader', False)
        
        # Quality settings
        quality = data.get('quality', {})
        profile.video_format = quality.get('video_format', 'best[height<=1080]')
        profile.audio_format = quality.get('audio_format', 'best')
        profile.prefer_free_codecs = quality.get('prefer_free_codecs', False)
        profile.max_filesize = quality.get('max_filesize')
        
        # Download options
        download = data.get('download', {})
        profile.concurrent_downloads = download.get('concurrent_downloads', 3)
        profile.max_retries = download.get('max_retries', 3)
        profile.retry_delay = download.get('retry_delay', 1.0)
        profile.timeout = download.get('timeout', 30)
        profile.rate_limit = download.get('rate_limit')
        
        # Post-processing
        post_proc = data.get('post_processing', {})
        profile.extract_audio = post_proc.get('extract_audio', False)
        profile.write_subtitles = post_proc.get('write_subtitles', False)
        profile.write_thumbnail = post_proc.get('write_thumbnail', True)
        profile.write_info_json = post_proc.get('write_info_json', False)
        profile.embed_metadata = post_proc.get('embed_metadata', True)
        profile.convert_format = post_proc.get('convert_format')
        
        # Engine preferences
        engines = data.get('engines', {})
        profile.preferred_engine = engines.get('preferred', 'auto')
        profile.fallback_enabled = engines.get('fallback_enabled', True)
        profile.engine_specific = engines.get('engine_specific', {})
        
        # Platform overrides
        profile.platform_overrides = data.get('platforms', {})
        
        # Filters
        filters = data.get('filters', {})
        profile.min_duration = filters.get('min_duration')
        profile.max_duration = filters.get('max_duration')
        profile.skip_live_streams = filters.get('skip_live_streams', False)
        profile.skip_premieres = filters.get('skip_premieres', False)
        profile.allowed_extensions = filters.get('allowed_extensions', [])
        profile.blocked_uploaders = filters.get('blocked_uploaders', [])
        
        # Notifications
        notifications = data.get('notifications', {})
        profile.notify_on_start = notifications.get('on_start', False)
        profile.notify_on_complete = notifications.get('on_complete', True)
        profile.notify_on_error = notifications.get('on_error', True)
        profile.notify_on_batch_complete = notifications.get('on_batch_complete', True)
        
        return profile
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary"""
        return {
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'output': {
                'path': self.output_path,
                'filename_template': self.filename_template,
                'create_subdirs': self.create_subdirs,
                'organize_by_uploader': self.organize_by_uploader
            },
            'quality': {
                'video_format': self.video_format,
                'audio_format': self.audio_format,
                'prefer_free_codecs': self.prefer_free_codecs,
                'max_filesize': self.max_filesize
            },
            'download': {
                'concurrent_downloads': self.concurrent_downloads,
                'max_retries': self.max_retries,
                'retry_delay': self.retry_delay,
                'timeout': self.timeout,
                'rate_limit': self.rate_limit
            },
            'post_processing': {
                'extract_audio': self.extract_audio,
                'write_subtitles': self.write_subtitles,
                'write_thumbnail': self.write_thumbnail,
                'write_info_json': self.write_info_json,
                'embed_metadata': self.embed_metadata,
                'convert_format': self.convert_format
            },
            'engines': {
                'preferred': self.preferred_engine,
                'fallback_enabled': self.fallback_enabled,
                'engine_specific': self.engine_specific
            },
            'platforms': self.platform_overrides,
            'filters': {
                'min_duration': self.min_duration,
                'max_duration': self.max_duration,
                'skip_live_streams': self.skip_live_streams,
                'skip_premieres': self.skip_premieres,
                'allowed_extensions': self.allowed_extensions,
                'blocked_uploaders': self.blocked_uploaders
            },
            'notifications': {
                'on_start': self.notify_on_start,
                'on_complete': self.notify_on_complete,
                'on_error': self.notify_on_error,
                'on_batch_complete': self.notify_on_batch_complete
            }
        }
    
    def to_yaml(self, yaml_path: Path):
        """Save profile to YAML file"""
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, indent=2)
    
    def validate(self) -> List[str]:
        """Validate profile configuration and return list of errors"""
        errors = []
        
        if not self.name or not self.name.strip():
            errors.append("Profile name cannot be empty")
        
        if self.concurrent_downloads < 1:
            errors.append("Concurrent downloads must be at least 1")
        
        if self.max_retries < 0:
            errors.append("Max retries cannot be negative")
        
        if self.retry_delay < 0:
            errors.append("Retry delay cannot be negative")
        
        if self.timeout < 1:
            errors.append("Timeout must be at least 1 second")
        
        if self.min_duration is not None and self.min_duration < 0:
            errors.append("Min duration cannot be negative")
        
        if self.max_duration is not None and self.max_duration < 0:
            errors.append("Max duration cannot be negative")
        
        if (self.min_duration is not None and self.max_duration is not None and 
            self.min_duration > self.max_duration):
            errors.append("Min duration cannot be greater than max duration")
        
        return errors
    
    def get_platform_config(self, platform: str) -> Dict[str, Any]:
        """Get configuration for a specific platform"""
        base_config = self.to_dict()
        platform_config = self.platform_overrides.get(platform, {})
        
        # Deep merge platform overrides
        merged_config = self._deep_merge(base_config, platform_config)
        return merged_config
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result

class ProfileManager:
    """Manages download profiles"""
    
    def __init__(self, profiles_dir: Optional[Path] = None, user_profiles_dir: Optional[Path] = None):
        self.profiles_dir = profiles_dir or Path(__file__).parent / "profiles"
        self.user_profiles_dir = user_profiles_dir or Path.home() / ".grabby" / "profiles"
        
        # Loaded profiles
        self.profiles: Dict[str, DownloadProfile] = {}
        
        # Default profile name
        self.default_profile_name = "default"
        
        # Ensure directories exist
        self.user_profiles_dir.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Initialize profile manager and load all profiles"""
        await self.load_builtin_profiles()
        await self.load_user_profiles()
        
        logger.info(f"Loaded {len(self.profiles)} profiles")
    
    async def load_builtin_profiles(self):
        """Load built-in profiles from profiles directory"""
        if not self.profiles_dir.exists():
            logger.warning(f"Built-in profiles directory not found: {self.profiles_dir}")
            return
        
        for yaml_file in self.profiles_dir.glob("*.yaml"):
            try:
                profile = DownloadProfile.from_yaml(yaml_file)
                profile.is_builtin = True
                
                # Validate profile
                errors = profile.validate()
                if errors:
                    logger.error(f"Invalid built-in profile {yaml_file.name}: {errors}")
                    continue
                
                self.profiles[profile.name] = profile
                logger.debug(f"Loaded built-in profile: {profile.name}")
                
            except Exception as e:
                logger.error(f"Failed to load built-in profile {yaml_file}: {e}")
    
    async def load_user_profiles(self):
        """Load user-defined profiles"""
        for yaml_file in self.user_profiles_dir.glob("*.yaml"):
            try:
                profile = DownloadProfile.from_yaml(yaml_file)
                profile.is_builtin = False
                
                # Validate profile
                errors = profile.validate()
                if errors:
                    logger.error(f"Invalid user profile {yaml_file.name}: {errors}")
                    continue
                
                self.profiles[profile.name] = profile
                logger.debug(f"Loaded user profile: {profile.name}")
                
            except Exception as e:
                logger.error(f"Failed to load user profile {yaml_file}: {e}")
    
    def get_profile(self, name: str) -> Optional[DownloadProfile]:
        """Get a profile by name"""
        return self.profiles.get(name)
    
    def get_default_profile(self) -> DownloadProfile:
        """Get the default profile"""
        profile = self.profiles.get(self.default_profile_name)
        if not profile:
            # Create a basic default profile if none exists
            profile = DownloadProfile(name=self.default_profile_name)
            self.profiles[self.default_profile_name] = profile
        
        return profile
    
    def list_profiles(self) -> List[str]:
        """Get list of all profile names"""
        return list(self.profiles.keys())
    
    def get_profile_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all profiles"""
        info = {}
        
        for name, profile in self.profiles.items():
            info[name] = {
                'name': profile.name,
                'description': profile.description,
                'version': profile.version,
                'is_builtin': profile.is_builtin,
                'created_at': profile.created_at.isoformat(),
                'updated_at': profile.updated_at.isoformat()
            }
        
        return info
    
    async def create_profile(self, profile: DownloadProfile) -> bool:
        """Create a new user profile"""
        # Validate profile
        errors = profile.validate()
        if errors:
            logger.error(f"Cannot create invalid profile: {errors}")
            return False
        
        # Check if profile already exists
        if profile.name in self.profiles:
            existing = self.profiles[profile.name]
            if existing.is_builtin:
                logger.error(f"Cannot override built-in profile: {profile.name}")
                return False
        
        # Save to user profiles directory
        yaml_path = self.user_profiles_dir / f"{profile.name}.yaml"
        
        try:
            profile.is_builtin = False
            profile.updated_at = datetime.now()
            profile.to_yaml(yaml_path)
            
            self.profiles[profile.name] = profile
            logger.info(f"Created user profile: {profile.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create profile {profile.name}: {e}")
            return False
    
    async def update_profile(self, name: str, updates: Dict[str, Any]) -> bool:
        """Update an existing profile"""
        profile = self.profiles.get(name)
        if not profile:
            logger.error(f"Profile not found: {name}")
            return False
        
        if profile.is_builtin:
            logger.error(f"Cannot modify built-in profile: {name}")
            return False
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        profile.updated_at = datetime.now()
        
        # Validate updated profile
        errors = profile.validate()
        if errors:
            logger.error(f"Updated profile is invalid: {errors}")
            return False
        
        # Save to file
        yaml_path = self.user_profiles_dir / f"{profile.name}.yaml"
        
        try:
            profile.to_yaml(yaml_path)
            logger.info(f"Updated user profile: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update profile {name}: {e}")
            return False
    
    async def delete_profile(self, name: str) -> bool:
        """Delete a user profile"""
        profile = self.profiles.get(name)
        if not profile:
            logger.error(f"Profile not found: {name}")
            return False
        
        if profile.is_builtin:
            logger.error(f"Cannot delete built-in profile: {name}")
            return False
        
        # Remove from memory
        del self.profiles[name]
        
        # Remove file
        yaml_path = self.user_profiles_dir / f"{name}.yaml"
        
        try:
            if yaml_path.exists():
                yaml_path.unlink()
            
            logger.info(f"Deleted user profile: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete profile {name}: {e}")
            return False
    
    async def duplicate_profile(self, source_name: str, new_name: str) -> bool:
        """Duplicate an existing profile with a new name"""
        source_profile = self.profiles.get(source_name)
        if not source_profile:
            logger.error(f"Source profile not found: {source_name}")
            return False
        
        if new_name in self.profiles:
            logger.error(f"Profile already exists: {new_name}")
            return False
        
        # Create new profile from source
        new_profile_data = source_profile.to_dict()
        new_profile_data['name'] = new_name
        new_profile_data['description'] = f"Copy of {source_profile.description}"
        
        new_profile = DownloadProfile.from_dict(new_profile_data)
        
        return await self.create_profile(new_profile)
    
    def set_default_profile(self, name: str) -> bool:
        """Set the default profile"""
        if name not in self.profiles:
            logger.error(f"Profile not found: {name}")
            return False
        
        self.default_profile_name = name
        logger.info(f"Set default profile to: {name}")
        return True

# Example usage
async def main():
    """Example usage of profile manager"""
    
    # Create profile manager
    manager = ProfileManager()
    await manager.initialize()
    
    # List available profiles
    profiles = manager.list_profiles()
    print(f"Available profiles: {profiles}")
    
    # Get default profile
    default = manager.get_default_profile()
    print(f"Default profile: {default.name} - {default.description}")
    
    # Get profile info
    info = manager.get_profile_info()
    for name, details in info.items():
        print(f"  {name}: {details['description']} ({'built-in' if details['is_builtin'] else 'user'})")

if __name__ == "__main__":
    asyncio.run(main())
