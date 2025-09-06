"""
Settings Manager for Grabby Video Downloader
Handles global application settings and user preferences
"""
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field, asdict
import json
import yaml
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class GlobalSettings:
    """Global application settings"""
    
    # General settings
    default_profile: str = "default"
    auto_update_check: bool = True
    log_level: str = "INFO"
    max_log_files: int = 10
    
    # Download defaults
    default_download_path: str = "./downloads"
    temp_directory: str = "./temp"
    max_concurrent_downloads: int = 3
    auto_cleanup_temp: bool = True
    
    # Network settings
    connection_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    user_agent: str = "Grabby/1.0"
    proxy_url: Optional[str] = None
    
    # Database settings
    database_type: str = "sqlite"  # sqlite, postgresql
    database_url: str = "sqlite:///grabby.db"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    
    # Cache settings
    enable_cache: bool = True
    cache_type: str = "memory"  # memory, redis
    cache_ttl: int = 3600  # seconds
    redis_url: str = "redis://localhost:6379/0"
    
    # Plugin settings
    enable_plugins: bool = True
    plugin_directories: list = field(default_factory=lambda: ["./plugins"])
    auto_load_plugins: bool = True
    
    # UI settings
    theme: str = "dark"  # dark, light, auto
    show_notifications: bool = True
    minimize_to_tray: bool = True
    start_minimized: bool = False
    
    # API settings
    api_enabled: bool = True
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_cors_origins: list = field(default_factory=lambda: ["*"])
    
    # WebSocket settings
    websocket_enabled: bool = True
    websocket_max_connections: int = 100
    websocket_ping_interval: int = 30
    
    # Security settings
    api_key_required: bool = False
    api_key: Optional[str] = None
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    
    # Advanced settings
    debug_mode: bool = False
    performance_monitoring: bool = False
    telemetry_enabled: bool = False
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GlobalSettings':
        """Create settings from dictionary"""
        # Handle datetime fields
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        # Create instance with only valid fields
        valid_fields = {f.name for f in cls.__dataclass_fields__}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        return cls(**filtered_data)
    
    def validate(self) -> list[str]:
        """Validate settings and return list of errors"""
        errors = []
        
        if self.max_concurrent_downloads < 1:
            errors.append("Max concurrent downloads must be at least 1")
        
        if self.connection_timeout < 1:
            errors.append("Connection timeout must be at least 1 second")
        
        if self.max_retries < 0:
            errors.append("Max retries cannot be negative")
        
        if self.retry_delay < 0:
            errors.append("Retry delay cannot be negative")
        
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            errors.append("Invalid log level")
        
        if self.database_type not in ["sqlite", "postgresql"]:
            errors.append("Invalid database type")
        
        if self.cache_type not in ["memory", "redis"]:
            errors.append("Invalid cache type")
        
        if self.theme not in ["dark", "light", "auto"]:
            errors.append("Invalid theme")
        
        if self.api_port < 1 or self.api_port > 65535:
            errors.append("API port must be between 1 and 65535")
        
        if self.database_pool_size < 1:
            errors.append("Database pool size must be at least 1")
        
        if self.cache_ttl < 0:
            errors.append("Cache TTL cannot be negative")
        
        return errors

class SettingsManager:
    """Manages global application settings"""
    
    def __init__(self, settings_file: Optional[Path] = None):
        self.settings_file = settings_file or Path.home() / ".grabby" / "settings.json"
        self.settings: GlobalSettings = GlobalSettings()
        
        # Ensure settings directory exists
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Initialize settings manager and load settings"""
        await self.load_settings()
        logger.info("Settings manager initialized")
    
    async def load_settings(self):
        """Load settings from file"""
        if not self.settings_file.exists():
            logger.info("Settings file not found, using defaults")
            await self.save_settings()
            return
        
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.settings = GlobalSettings.from_dict(data)
            
            # Validate loaded settings
            errors = self.settings.validate()
            if errors:
                logger.warning(f"Invalid settings found: {errors}")
                # Reset to defaults for invalid settings
                self.settings = GlobalSettings()
                await self.save_settings()
            
            logger.info("Settings loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            logger.info("Using default settings")
            self.settings = GlobalSettings()
            await self.save_settings()
    
    async def save_settings(self):
        """Save settings to file"""
        try:
            self.settings.updated_at = datetime.now()
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings.to_dict(), f, indent=2, default=str)
            
            logger.debug("Settings saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            raise
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a specific setting value"""
        return getattr(self.settings, key, default)
    
    async def update_setting(self, key: str, value: Any) -> bool:
        """Update a specific setting"""
        if not hasattr(self.settings, key):
            logger.error(f"Unknown setting: {key}")
            return False
        
        old_value = getattr(self.settings, key)
        setattr(self.settings, key, value)
        
        # Validate updated settings
        errors = self.settings.validate()
        if errors:
            # Revert change
            setattr(self.settings, key, old_value)
            logger.error(f"Invalid setting value: {errors}")
            return False
        
        await self.save_settings()
        logger.info(f"Updated setting {key}: {old_value} -> {value}")
        return True
    
    async def update_settings(self, updates: Dict[str, Any]) -> bool:
        """Update multiple settings at once"""
        # Store original values for rollback
        original_values = {}
        
        try:
            # Apply all updates
            for key, value in updates.items():
                if not hasattr(self.settings, key):
                    logger.error(f"Unknown setting: {key}")
                    return False
                
                original_values[key] = getattr(self.settings, key)
                setattr(self.settings, key, value)
            
            # Validate all changes
            errors = self.settings.validate()
            if errors:
                # Rollback all changes
                for key, value in original_values.items():
                    setattr(self.settings, key, value)
                logger.error(f"Invalid settings: {errors}")
                return False
            
            await self.save_settings()
            logger.info(f"Updated {len(updates)} settings")
            return True
            
        except Exception as e:
            # Rollback all changes
            for key, value in original_values.items():
                setattr(self.settings, key, value)
            logger.error(f"Failed to update settings: {e}")
            return False
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings as dictionary"""
        return self.settings.to_dict()
    
    async def reset_settings(self):
        """Reset all settings to defaults"""
        self.settings = GlobalSettings()
        await self.save_settings()
        logger.info("Settings reset to defaults")
    
    async def export_settings(self, export_path: Path, format: str = "json"):
        """Export settings to file"""
        try:
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format.lower() == "json":
                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(self.settings.to_dict(), f, indent=2, default=str)
            
            elif format.lower() == "yaml":
                with open(export_path, 'w', encoding='utf-8') as f:
                    yaml.dump(self.settings.to_dict(), f, default_flow_style=False, indent=2)
            
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            logger.info(f"Settings exported to {export_path}")
            
        except Exception as e:
            logger.error(f"Failed to export settings: {e}")
            raise
    
    async def import_settings(self, import_path: Path, format: str = "json"):
        """Import settings from file"""
        try:
            if not import_path.exists():
                raise FileNotFoundError(f"Import file not found: {import_path}")
            
            if format.lower() == "json":
                with open(import_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            elif format.lower() == "yaml":
                with open(import_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
            
            else:
                raise ValueError(f"Unsupported import format: {format}")
            
            # Create settings from imported data
            imported_settings = GlobalSettings.from_dict(data)
            
            # Validate imported settings
            errors = imported_settings.validate()
            if errors:
                raise ValueError(f"Invalid imported settings: {errors}")
            
            self.settings = imported_settings
            await self.save_settings()
            
            logger.info(f"Settings imported from {import_path}")
            
        except Exception as e:
            logger.error(f"Failed to import settings: {e}")
            raise
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return {
            'type': self.settings.database_type,
            'url': self.settings.database_url,
            'pool_size': self.settings.database_pool_size,
            'max_overflow': self.settings.database_max_overflow
        }
    
    def get_cache_config(self) -> Dict[str, Any]:
        """Get cache configuration"""
        return {
            'enabled': self.settings.enable_cache,
            'type': self.settings.cache_type,
            'ttl': self.settings.cache_ttl,
            'redis_url': self.settings.redis_url
        }
    
    def get_api_config(self) -> Dict[str, Any]:
        """Get API configuration"""
        return {
            'enabled': self.settings.api_enabled,
            'host': self.settings.api_host,
            'port': self.settings.api_port,
            'cors_origins': self.settings.api_cors_origins,
            'key_required': self.settings.api_key_required,
            'api_key': self.settings.api_key,
            'rate_limit_enabled': self.settings.rate_limit_enabled,
            'rate_limit_requests': self.settings.rate_limit_requests,
            'rate_limit_window': self.settings.rate_limit_window
        }
    
    def get_websocket_config(self) -> Dict[str, Any]:
        """Get WebSocket configuration"""
        return {
            'enabled': self.settings.websocket_enabled,
            'max_connections': self.settings.websocket_max_connections,
            'ping_interval': self.settings.websocket_ping_interval
        }

# Global settings manager instance
_settings_manager: Optional[SettingsManager] = None

async def get_settings_manager() -> SettingsManager:
    """Get global settings manager instance"""
    global _settings_manager
    
    if _settings_manager is None:
        _settings_manager = SettingsManager()
        await _settings_manager.initialize()
    
    return _settings_manager

# Example usage
async def main():
    """Example usage of settings manager"""
    
    # Get settings manager
    manager = await get_settings_manager()
    
    # Get current settings
    settings = manager.get_all_settings()
    print(f"Current settings: {json.dumps(settings, indent=2, default=str)}")
    
    # Update a setting
    success = await manager.update_setting('max_concurrent_downloads', 5)
    print(f"Update successful: {success}")
    
    # Update multiple settings
    updates = {
        'theme': 'light',
        'show_notifications': False
    }
    success = await manager.update_settings(updates)
    print(f"Batch update successful: {success}")

if __name__ == "__main__":
    asyncio.run(main())
