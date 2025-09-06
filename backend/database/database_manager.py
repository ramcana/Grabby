"""
Database Manager for Grabby Video Downloader
Handles SQLite/PostgreSQL operations with async support
"""
import asyncio
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import json
import aiosqlite

try:
    import asyncpg
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

from .models import (
    DownloadRecord, PlaylistRecord, UserSettings, DownloadStatus,
    DOWNLOAD_RECORDS_SCHEMA, PLAYLIST_RECORDS_SCHEMA, USER_SETTINGS_SCHEMA, INDEXES
)
from .migrations import MigrationManager

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database operations for download history and metadata"""
    
    def __init__(self, 
                 database_url: str = "sqlite:///./grabby.db",
                 auto_migrate: bool = True):
        
        self.database_url = database_url
        self.auto_migrate = auto_migrate
        self.db_type = "sqlite" if database_url.startswith("sqlite") else "postgresql"
        
        # Connection objects
        self.sqlite_db: Optional[aiosqlite.Connection] = None
        self.postgres_pool: Optional[Any] = None
        
        # Migration manager
        self.migration_manager = MigrationManager(self)
        
        # Initialize database path for SQLite
        if self.db_type == "sqlite":
            db_path = database_url.replace("sqlite:///", "")
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Initialize database connection and schema"""
        try:
            if self.db_type == "sqlite":
                await self._init_sqlite()
            else:
                await self._init_postgresql()
            
            # Run migrations if enabled
            if self.auto_migrate:
                await self.migration_manager.run_migrations()
            
            logger.info(f"Database initialized: {self.database_url}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def _init_sqlite(self):
        """Initialize SQLite connection"""
        self.sqlite_db = await aiosqlite.connect(self.db_path)
        self.sqlite_db.row_factory = aiosqlite.Row
        
        # Create tables
        await self.sqlite_db.execute(DOWNLOAD_RECORDS_SCHEMA)
        await self.sqlite_db.execute(PLAYLIST_RECORDS_SCHEMA)
        await self.sqlite_db.execute(USER_SETTINGS_SCHEMA)
        
        # Create indexes
        for index_sql in INDEXES:
            await self.sqlite_db.execute(index_sql)
        
        await self.sqlite_db.commit()
    
    async def _init_postgresql(self):
        """Initialize PostgreSQL connection"""
        if not POSTGRES_AVAILABLE:
            raise Exception("asyncpg not available for PostgreSQL support")
        
        # Parse connection string
        # Format: postgresql://user:password@host:port/database
        self.postgres_pool = await asyncpg.create_pool(self.database_url)
        
        # Create tables (PostgreSQL syntax)
        async with self.postgres_pool.acquire() as conn:
            # Convert SQLite schema to PostgreSQL
            pg_download_schema = DOWNLOAD_RECORDS_SCHEMA.replace(
                "INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY"
            ).replace("TIMESTAMP", "TIMESTAMPTZ")
            
            pg_playlist_schema = PLAYLIST_RECORDS_SCHEMA.replace(
                "INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY"
            ).replace("TIMESTAMP", "TIMESTAMPTZ")
            
            pg_settings_schema = USER_SETTINGS_SCHEMA.replace(
                "INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY"
            ).replace("TIMESTAMP", "TIMESTAMPTZ")
            
            await conn.execute(pg_download_schema)
            await conn.execute(pg_playlist_schema)
            await conn.execute(pg_settings_schema)
            
            # Create indexes
            for index_sql in INDEXES:
                await conn.execute(index_sql)
    
    async def close(self):
        """Close database connections"""
        if self.sqlite_db:
            await self.sqlite_db.close()
        if self.postgres_pool:
            await self.postgres_pool.close()
    
    # Download Records Operations
    
    async def add_download_record(self, record: DownloadRecord) -> int:
        """Add a new download record"""
        if self.db_type == "sqlite":
            return await self._add_download_record_sqlite(record)
        else:
            return await self._add_download_record_postgres(record)
    
    async def _add_download_record_sqlite(self, record: DownloadRecord) -> int:
        """Add download record to SQLite"""
        sql = """
        INSERT INTO download_records (
            url, title, description, uploader, upload_date, duration, view_count, like_count,
            status, engine_used, file_path, file_size, format_id, quality,
            created_at, started_at, completed_at, error_message, retry_count,
            thumbnail_url, thumbnail_path, subtitles_path, info_json_path,
            playlist_id, playlist_index, extra_metadata, download_options
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        values = (
            record.url, record.title, record.description, record.uploader,
            record.upload_date, record.duration, record.view_count, record.like_count,
            record.status.value, record.engine_used.value if record.engine_used else None,
            record.file_path, record.file_size, record.format_id, record.quality,
            record.created_at, record.started_at, record.completed_at,
            record.error_message, record.retry_count,
            record.thumbnail_url, record.thumbnail_path, record.subtitles_path, record.info_json_path,
            record.playlist_id, record.playlist_index,
            json.dumps(record.extra_metadata), json.dumps(record.download_options)
        )
        
        cursor = await self.sqlite_db.execute(sql, values)
        await self.sqlite_db.commit()
        return cursor.lastrowid
    
    async def _add_download_record_postgres(self, record: DownloadRecord) -> int:
        """Add download record to PostgreSQL"""
        sql = """
        INSERT INTO download_records (
            url, title, description, uploader, upload_date, duration, view_count, like_count,
            status, engine_used, file_path, file_size, format_id, quality,
            created_at, started_at, completed_at, error_message, retry_count,
            thumbnail_url, thumbnail_path, subtitles_path, info_json_path,
            playlist_id, playlist_index, extra_metadata, download_options
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27)
        RETURNING id
        """
        
        values = (
            record.url, record.title, record.description, record.uploader,
            record.upload_date, record.duration, record.view_count, record.like_count,
            record.status.value, record.engine_used.value if record.engine_used else None,
            record.file_path, record.file_size, record.format_id, record.quality,
            record.created_at, record.started_at, record.completed_at,
            record.error_message, record.retry_count,
            record.thumbnail_url, record.thumbnail_path, record.subtitles_path, record.info_json_path,
            record.playlist_id, record.playlist_index,
            json.dumps(record.extra_metadata), json.dumps(record.download_options)
        )
        
        async with self.postgres_pool.acquire() as conn:
            result = await conn.fetchval(sql, *values)
            return result
    
    async def update_download_record(self, record_id: int, updates: Dict[str, Any]) -> bool:
        """Update a download record"""
        if not updates:
            return False
        
        # Build SET clause
        set_clauses = []
        values = []
        
        for key, value in updates.items():
            if key in ['status', 'engine_used'] and hasattr(value, 'value'):
                value = value.value
            elif key in ['extra_metadata', 'download_options'] and isinstance(value, dict):
                value = json.dumps(value)
            
            set_clauses.append(f"{key} = ?")
            values.append(value)
        
        values.append(record_id)
        
        sql = f"UPDATE download_records SET {', '.join(set_clauses)} WHERE id = ?"
        
        if self.db_type == "sqlite":
            await self.sqlite_db.execute(sql, values)
            await self.sqlite_db.commit()
        else:
            # Convert to PostgreSQL parameter style
            pg_sql = sql
            for i in range(len(values)):
                pg_sql = pg_sql.replace("?", f"${i+1}", 1)
            
            async with self.postgres_pool.acquire() as conn:
                await conn.execute(pg_sql, *values)
        
        return True
    
    async def get_download_record(self, record_id: int) -> Optional[DownloadRecord]:
        """Get a download record by ID"""
        sql = "SELECT * FROM download_records WHERE id = ?"
        
        if self.db_type == "sqlite":
            cursor = await self.sqlite_db.execute(sql, (record_id,))
            row = await cursor.fetchone()
        else:
            async with self.postgres_pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM download_records WHERE id = $1", record_id)
        
        if row:
            return self._row_to_download_record(row)
        return None
    
    async def get_download_records(self, 
                                  status: Optional[DownloadStatus] = None,
                                  limit: int = 100,
                                  offset: int = 0,
                                  search: Optional[str] = None) -> List[DownloadRecord]:
        """Get download records with filtering"""
        
        conditions = []
        values = []
        
        if status:
            conditions.append("status = ?")
            values.append(status.value)
        
        if search:
            conditions.append("(title LIKE ? OR uploader LIKE ? OR url LIKE ?)")
            search_term = f"%{search}%"
            values.extend([search_term, search_term, search_term])
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        sql = f"""
        SELECT * FROM download_records 
        {where_clause}
        ORDER BY created_at DESC 
        LIMIT ? OFFSET ?
        """
        
        values.extend([limit, offset])
        
        if self.db_type == "sqlite":
            cursor = await self.sqlite_db.execute(sql, values)
            rows = await cursor.fetchall()
        else:
            # Convert to PostgreSQL parameter style
            pg_sql = sql
            for i in range(len(values)):
                pg_sql = pg_sql.replace("?", f"${i+1}", 1)
            
            async with self.postgres_pool.acquire() as conn:
                rows = await conn.fetch(pg_sql, *values)
        
        return [self._row_to_download_record(row) for row in rows]
    
    async def delete_download_record(self, record_id: int) -> bool:
        """Delete a download record"""
        sql = "DELETE FROM download_records WHERE id = ?"
        
        if self.db_type == "sqlite":
            cursor = await self.sqlite_db.execute(sql, (record_id,))
            await self.sqlite_db.commit()
            return cursor.rowcount > 0
        else:
            async with self.postgres_pool.acquire() as conn:
                result = await conn.execute("DELETE FROM download_records WHERE id = $1", record_id)
                return result.split()[-1] != "0"
    
    # Playlist Records Operations
    
    async def add_playlist_record(self, record: PlaylistRecord) -> int:
        """Add a new playlist record"""
        sql = """
        INSERT INTO playlist_records (
            url, title, description, uploader, total_entries, downloaded_entries, failed_entries,
            status, created_at, started_at, completed_at, thumbnail_url, extra_metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        values = (
            record.url, record.title, record.description, record.uploader,
            record.total_entries, record.downloaded_entries, record.failed_entries,
            record.status.value, record.created_at, record.started_at, record.completed_at,
            record.thumbnail_url, json.dumps(record.extra_metadata)
        )
        
        if self.db_type == "sqlite":
            cursor = await self.sqlite_db.execute(sql, values)
            await self.sqlite_db.commit()
            return cursor.lastrowid
        else:
            pg_sql = sql.replace("?", lambda m, i=[0]: f"${i[0]:=i[0]+1}")
            async with self.postgres_pool.acquire() as conn:
                return await conn.fetchval(pg_sql + " RETURNING id", *values)
    
    # User Settings Operations
    
    async def get_setting(self, key: str) -> Optional[Any]:
        """Get a user setting value"""
        sql = "SELECT * FROM user_settings WHERE key = ?"
        
        if self.db_type == "sqlite":
            cursor = await self.sqlite_db.execute(sql, (key,))
            row = await cursor.fetchone()
        else:
            async with self.postgres_pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM user_settings WHERE key = $1", key)
        
        if row:
            setting = UserSettings(
                id=row['id'],
                key=row['key'],
                value=row['value'],
                value_type=row['value_type'],
                description=row['description'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            return setting.get_typed_value()
        
        return None
    
    async def set_setting(self, key: str, value: Any, description: str = "") -> bool:
        """Set a user setting value"""
        setting = UserSettings(key=key, description=description)
        setting.set_typed_value(value)
        
        # Check if setting exists
        existing = await self.get_setting(key)
        
        if existing is not None:
            # Update existing
            sql = "UPDATE user_settings SET value = ?, value_type = ?, updated_at = ? WHERE key = ?"
            values = (setting.value, setting.value_type, setting.updated_at, key)
        else:
            # Insert new
            sql = """
            INSERT INTO user_settings (key, value, value_type, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            values = (setting.key, setting.value, setting.value_type, setting.description,
                     setting.created_at, setting.updated_at)
        
        if self.db_type == "sqlite":
            await self.sqlite_db.execute(sql, values)
            await self.sqlite_db.commit()
        else:
            # Convert to PostgreSQL parameter style
            pg_sql = sql
            for i in range(len(values)):
                pg_sql = pg_sql.replace("?", f"${i+1}", 1)
            
            async with self.postgres_pool.acquire() as conn:
                await conn.execute(pg_sql, *values)
        
        return True
    
    # Statistics and Analytics
    
    async def get_download_statistics(self) -> Dict[str, Any]:
        """Get download statistics"""
        stats = {}
        
        # Total downloads by status
        sql = "SELECT status, COUNT(*) as count FROM download_records GROUP BY status"
        
        if self.db_type == "sqlite":
            cursor = await self.sqlite_db.execute(sql)
            rows = await cursor.fetchall()
        else:
            async with self.postgres_pool.acquire() as conn:
                rows = await conn.fetch(sql)
        
        stats['by_status'] = {row['status']: row['count'] for row in rows}
        
        # Total file size
        sql = "SELECT SUM(file_size) as total_size FROM download_records WHERE file_size IS NOT NULL"
        
        if self.db_type == "sqlite":
            cursor = await self.sqlite_db.execute(sql)
            row = await cursor.fetchone()
        else:
            async with self.postgres_pool.acquire() as conn:
                row = await conn.fetchrow(sql)
        
        stats['total_size_bytes'] = row['total_size'] or 0
        
        # Downloads per day (last 30 days)
        sql = """
        SELECT DATE(created_at) as date, COUNT(*) as count 
        FROM download_records 
        WHERE created_at >= datetime('now', '-30 days')
        GROUP BY DATE(created_at)
        ORDER BY date
        """
        
        if self.db_type == "sqlite":
            cursor = await self.sqlite_db.execute(sql)
            rows = await cursor.fetchall()
        else:
            pg_sql = """
            SELECT DATE(created_at) as date, COUNT(*) as count 
            FROM download_records 
            WHERE created_at >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(created_at)
            ORDER BY date
            """
            async with self.postgres_pool.acquire() as conn:
                rows = await conn.fetch(pg_sql)
        
        stats['daily_downloads'] = {str(row['date']): row['count'] for row in rows}
        
        return stats
    
    # Helper methods
    
    def _row_to_download_record(self, row) -> DownloadRecord:
        """Convert database row to DownloadRecord"""
        return DownloadRecord(
            id=row['id'],
            url=row['url'],
            title=row['title'] or "",
            description=row['description'] or "",
            uploader=row['uploader'] or "",
            upload_date=row['upload_date'],
            duration=row['duration'],
            view_count=row['view_count'],
            like_count=row['like_count'],
            status=DownloadStatus(row['status']),
            engine_used=row['engine_used'],
            file_path=row['file_path'] or "",
            file_size=row['file_size'],
            format_id=row['format_id'] or "",
            quality=row['quality'] or "",
            created_at=row['created_at'],
            started_at=row['started_at'],
            completed_at=row['completed_at'],
            error_message=row['error_message'] or "",
            retry_count=row['retry_count'] or 0,
            thumbnail_url=row['thumbnail_url'] or "",
            thumbnail_path=row['thumbnail_path'] or "",
            subtitles_path=row['subtitles_path'] or "",
            info_json_path=row['info_json_path'] or "",
            playlist_id=row['playlist_id'],
            playlist_index=row['playlist_index'],
            extra_metadata=json.loads(row['extra_metadata'] or '{}'),
            download_options=json.loads(row['download_options'] or '{}')
        )
