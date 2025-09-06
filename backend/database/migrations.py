"""
Database Migration Manager for Grabby Video Downloader
Handles database schema migrations and version management
"""
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class Migration:
    """Represents a single database migration"""
    
    def __init__(self, version: int, name: str, up_sql: str, down_sql: str = ""):
        self.version = version
        self.name = name
        self.up_sql = up_sql
        self.down_sql = down_sql
        self.applied_at: Optional[datetime] = None
    
    def __str__(self):
        return f"Migration {self.version}: {self.name}"

class MigrationManager:
    """Manages database migrations"""
    
    def __init__(self, database_manager):
        self.db = database_manager
        self.migrations: List[Migration] = []
        self._load_migrations()
    
    def _load_migrations(self):
        """Load all available migrations"""
        
        # Migration 001: Initial schema (already handled by database_manager)
        self.migrations.append(Migration(
            version=1,
            name="initial_schema",
            up_sql="-- Initial schema created by database_manager",
            down_sql="DROP TABLE IF EXISTS download_records; DROP TABLE IF EXISTS playlist_records; DROP TABLE IF EXISTS user_settings;"
        ))
        
        # Migration 002: Add indexes for better performance
        self.migrations.append(Migration(
            version=2,
            name="add_performance_indexes",
            up_sql="""
            CREATE INDEX IF NOT EXISTS idx_download_records_uploader ON download_records(uploader);
            CREATE INDEX IF NOT EXISTS idx_download_records_engine_used ON download_records(engine_used);
            CREATE INDEX IF NOT EXISTS idx_download_records_file_size ON download_records(file_size);
            """,
            down_sql="""
            DROP INDEX IF EXISTS idx_download_records_uploader;
            DROP INDEX IF EXISTS idx_download_records_engine_used;
            DROP INDEX IF EXISTS idx_download_records_file_size;
            """
        ))
        
        # Migration 003: Add full-text search support (SQLite only)
        self.migrations.append(Migration(
            version=3,
            name="add_fulltext_search",
            up_sql="""
            CREATE VIRTUAL TABLE IF NOT EXISTS download_records_fts USING fts5(
                title, description, uploader, content='download_records', content_rowid='id'
            );
            
            -- Populate FTS table
            INSERT INTO download_records_fts(rowid, title, description, uploader)
            SELECT id, title, description, uploader FROM download_records;
            
            -- Trigger to keep FTS in sync
            CREATE TRIGGER IF NOT EXISTS download_records_fts_insert AFTER INSERT ON download_records BEGIN
                INSERT INTO download_records_fts(rowid, title, description, uploader)
                VALUES (new.id, new.title, new.description, new.uploader);
            END;
            
            CREATE TRIGGER IF NOT EXISTS download_records_fts_delete AFTER DELETE ON download_records BEGIN
                INSERT INTO download_records_fts(download_records_fts, rowid, title, description, uploader)
                VALUES('delete', old.id, old.title, old.description, old.uploader);
            END;
            
            CREATE TRIGGER IF NOT EXISTS download_records_fts_update AFTER UPDATE ON download_records BEGIN
                INSERT INTO download_records_fts(download_records_fts, rowid, title, description, uploader)
                VALUES('delete', old.id, old.title, old.description, old.uploader);
                INSERT INTO download_records_fts(rowid, title, description, uploader)
                VALUES (new.id, new.title, new.description, new.uploader);
            END;
            """,
            down_sql="""
            DROP TRIGGER IF EXISTS download_records_fts_update;
            DROP TRIGGER IF EXISTS download_records_fts_delete;
            DROP TRIGGER IF EXISTS download_records_fts_insert;
            DROP TABLE IF EXISTS download_records_fts;
            """
        ))
        
        # Migration 004: Add download tags and categories
        self.migrations.append(Migration(
            version=4,
            name="add_tags_and_categories",
            up_sql="""
            ALTER TABLE download_records ADD COLUMN tags TEXT DEFAULT '';
            ALTER TABLE download_records ADD COLUMN category TEXT DEFAULT '';
            ALTER TABLE download_records ADD COLUMN rating INTEGER DEFAULT 0;
            
            CREATE INDEX IF NOT EXISTS idx_download_records_category ON download_records(category);
            CREATE INDEX IF NOT EXISTS idx_download_records_rating ON download_records(rating);
            """,
            down_sql="""
            -- SQLite doesn't support DROP COLUMN, so we'd need to recreate the table
            -- For now, just clear the data
            UPDATE download_records SET tags = '', category = '', rating = 0;
            """
        ))
        
        # Migration 005: Add download statistics table
        self.migrations.append(Migration(
            version=5,
            name="add_statistics_table",
            up_sql="""
            CREATE TABLE IF NOT EXISTS download_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                downloads_count INTEGER DEFAULT 0,
                downloads_size INTEGER DEFAULT 0,
                downloads_duration INTEGER DEFAULT 0,
                unique_uploaders INTEGER DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date)
            );
            
            CREATE INDEX IF NOT EXISTS idx_download_statistics_date ON download_statistics(date);
            """,
            down_sql="DROP TABLE IF EXISTS download_statistics;"
        ))
    
    async def create_migrations_table(self):
        """Create the migrations tracking table"""
        sql = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        if self.db.db_type == "sqlite":
            await self.db.sqlite_db.execute(sql)
            await self.db.sqlite_db.commit()
        else:
            pg_sql = sql.replace("INTEGER PRIMARY KEY", "INTEGER PRIMARY KEY").replace("TIMESTAMP", "TIMESTAMPTZ")
            async with self.db.postgres_pool.acquire() as conn:
                await conn.execute(pg_sql)
    
    async def get_applied_migrations(self) -> List[int]:
        """Get list of applied migration versions"""
        try:
            sql = "SELECT version FROM schema_migrations ORDER BY version"
            
            if self.db.db_type == "sqlite":
                cursor = await self.db.sqlite_db.execute(sql)
                rows = await cursor.fetchall()
            else:
                async with self.db.postgres_pool.acquire() as conn:
                    rows = await conn.fetch(sql)
            
            return [row['version'] for row in rows]
            
        except Exception:
            # Migrations table doesn't exist yet
            return []
    
    async def run_migrations(self):
        """Run all pending migrations"""
        await self.create_migrations_table()
        
        applied_versions = await self.get_applied_migrations()
        pending_migrations = [m for m in self.migrations if m.version not in applied_versions]
        
        if not pending_migrations:
            logger.info("No pending migrations")
            return
        
        logger.info(f"Running {len(pending_migrations)} pending migrations")
        
        for migration in pending_migrations:
            await self._apply_migration(migration)
    
    async def _apply_migration(self, migration: Migration):
        """Apply a single migration"""
        try:
            logger.info(f"Applying migration: {migration}")
            
            # Skip FTS migration for PostgreSQL
            if migration.name == "add_fulltext_search" and self.db.db_type == "postgresql":
                logger.info("Skipping FTS migration for PostgreSQL")
                await self._record_migration(migration)
                return
            
            # Execute migration SQL
            if self.db.db_type == "sqlite":
                # Split SQL statements and execute individually
                statements = [s.strip() for s in migration.up_sql.split(';') if s.strip()]
                for statement in statements:
                    if statement:
                        await self.db.sqlite_db.execute(statement)
                await self.db.sqlite_db.commit()
            else:
                # Convert SQLite-specific SQL to PostgreSQL
                pg_sql = self._convert_to_postgresql(migration.up_sql)
                async with self.db.postgres_pool.acquire() as conn:
                    await conn.execute(pg_sql)
            
            # Record migration as applied
            await self._record_migration(migration)
            
            logger.info(f"Successfully applied migration: {migration}")
            
        except Exception as e:
            logger.error(f"Failed to apply migration {migration}: {e}")
            raise
    
    async def _record_migration(self, migration: Migration):
        """Record migration as applied"""
        sql = "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)"
        values = (migration.version, migration.name, datetime.now())
        
        if self.db.db_type == "sqlite":
            await self.db.sqlite_db.execute(sql, values)
            await self.db.sqlite_db.commit()
        else:
            pg_sql = "INSERT INTO schema_migrations (version, name, applied_at) VALUES ($1, $2, $3)"
            async with self.db.postgres_pool.acquire() as conn:
                await conn.execute(pg_sql, *values)
    
    def _convert_to_postgresql(self, sqlite_sql: str) -> str:
        """Convert SQLite SQL to PostgreSQL SQL"""
        # Basic conversions
        pg_sql = sqlite_sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        pg_sql = pg_sql.replace("TIMESTAMP", "TIMESTAMPTZ")
        pg_sql = pg_sql.replace("datetime('now'", "NOW(")
        
        # Remove SQLite-specific features
        if "VIRTUAL TABLE" in pg_sql or "fts5" in pg_sql:
            return "-- FTS not supported in PostgreSQL"
        
        return pg_sql
    
    async def rollback_migration(self, version: int):
        """Rollback a specific migration"""
        migration = next((m for m in self.migrations if m.version == version), None)
        if not migration:
            raise ValueError(f"Migration version {version} not found")
        
        if not migration.down_sql:
            raise ValueError(f"Migration {version} has no rollback SQL")
        
        try:
            logger.info(f"Rolling back migration: {migration}")
            
            # Execute rollback SQL
            if self.db.db_type == "sqlite":
                statements = [s.strip() for s in migration.down_sql.split(';') if s.strip()]
                for statement in statements:
                    if statement:
                        await self.db.sqlite_db.execute(statement)
                await self.db.sqlite_db.commit()
            else:
                pg_sql = self._convert_to_postgresql(migration.down_sql)
                async with self.db.postgres_pool.acquire() as conn:
                    await conn.execute(pg_sql)
            
            # Remove migration record
            sql = "DELETE FROM schema_migrations WHERE version = ?"
            if self.db.db_type == "sqlite":
                await self.db.sqlite_db.execute(sql, (version,))
                await self.db.sqlite_db.commit()
            else:
                async with self.db.postgres_pool.acquire() as conn:
                    await conn.execute("DELETE FROM schema_migrations WHERE version = $1", version)
            
            logger.info(f"Successfully rolled back migration: {migration}")
            
        except Exception as e:
            logger.error(f"Failed to rollback migration {migration}: {e}")
            raise
    
    async def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status"""
        applied_versions = await self.get_applied_migrations()
        
        status = {
            'current_version': max(applied_versions) if applied_versions else 0,
            'latest_version': max(m.version for m in self.migrations),
            'applied_migrations': applied_versions,
            'pending_migrations': [m.version for m in self.migrations if m.version not in applied_versions],
            'total_migrations': len(self.migrations)
        }
        
        return status
