"""
Profile management commands for CLI
"""
import asyncio
import sys
from pathlib import Path
from typing import Optional
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
import yaml

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config.profile_manager import ProfileManager, DownloadProfile

console = Console()

@click.group()
def profiles():
    """Manage download profiles"""
    pass

@profiles.command()
def list():
    """List all available profiles"""
    
    async def list_profiles():
        try:
            manager = ProfileManager()
            await manager.initialize()
            
            profile_info = manager.get_profile_info()
            
            if not profile_info:
                console.print("📋 No profiles found")
                return
            
            table = Table(title="📋 Available Download Profiles")
            table.add_column("Name", style="cyan")
            table.add_column("Description", style="green")
            table.add_column("Type", style="yellow")
            table.add_column("Version", style="magenta")
            
            for name, info in profile_info.items():
                profile_type = "Built-in" if info['is_builtin'] else "User"
                table.add_row(
                    name,
                    info['description'][:50] + "..." if len(info['description']) > 50 else info['description'],
                    profile_type,
                    info['version']
                )
            
            console.print(table)
            
            # Show default profile
            default_profile = manager.get_default_profile()
            console.print(f"\n🎯 Default profile: [bold cyan]{default_profile.name}[/bold cyan]")
            
        except Exception as e:
            console.print(f"❌ Error listing profiles: {e}")
    
    asyncio.run(list_profiles())

@profiles.command()
@click.argument('name')
def show(name):
    """Show detailed information about a profile"""
    
    async def show_profile():
        try:
            manager = ProfileManager()
            await manager.initialize()
            
            profile = manager.get_profile(name)
            if not profile:
                console.print(f"❌ Profile not found: [red]{name}[/red]")
                available = manager.list_profiles()
                if available:
                    console.print(f"Available profiles: {', '.join(available)}")
                return
            
            # Create detailed view
            panel_content = []
            
            # Basic info
            panel_content.append(f"[bold]Description:[/bold] {profile.description}")
            panel_content.append(f"[bold]Version:[/bold] {profile.version}")
            panel_content.append(f"[bold]Type:[/bold] {'Built-in' if profile.is_builtin else 'User'}")
            panel_content.append("")
            
            # Output settings
            panel_content.append("[bold cyan]Output Settings:[/bold cyan]")
            panel_content.append(f"  Path: {profile.output_path}")
            panel_content.append(f"  Filename: {profile.filename_template}")
            panel_content.append(f"  Create subdirs: {profile.create_subdirs}")
            panel_content.append(f"  Organize by uploader: {profile.organize_by_uploader}")
            panel_content.append("")
            
            # Quality settings
            panel_content.append("[bold green]Quality Settings:[/bold green]")
            panel_content.append(f"  Video format: {profile.video_format}")
            panel_content.append(f"  Audio format: {profile.audio_format}")
            panel_content.append(f"  Max filesize: {profile.max_filesize or 'No limit'}")
            panel_content.append("")
            
            # Download options
            panel_content.append("[bold yellow]Download Options:[/bold yellow]")
            panel_content.append(f"  Concurrent downloads: {profile.concurrent_downloads}")
            panel_content.append(f"  Max retries: {profile.max_retries}")
            panel_content.append(f"  Timeout: {profile.timeout}s")
            panel_content.append(f"  Rate limit: {profile.rate_limit or 'None'}")
            panel_content.append("")
            
            # Engine preferences
            panel_content.append("[bold magenta]Engine Preferences:[/bold magenta]")
            panel_content.append(f"  Preferred: {profile.preferred_engine}")
            panel_content.append(f"  Fallback enabled: {profile.fallback_enabled}")
            
            if profile.platform_overrides:
                panel_content.append("")
                panel_content.append("[bold red]Platform Overrides:[/bold red]")
                for platform, overrides in profile.platform_overrides.items():
                    panel_content.append(f"  {platform}: {len(overrides)} settings")
            
            console.print(Panel("\n".join(panel_content), title=f"Profile: {name}"))
            
        except Exception as e:
            console.print(f"❌ Error showing profile: {e}")
    
    asyncio.run(show_profile())

@profiles.command()
@click.argument('source_name')
@click.argument('new_name')
def copy(source_name, new_name):
    """Copy an existing profile with a new name"""
    
    async def copy_profile():
        try:
            manager = ProfileManager()
            await manager.initialize()
            
            success = await manager.duplicate_profile(source_name, new_name)
            if success:
                console.print(f"✅ Profile copied: [cyan]{source_name}[/cyan] → [green]{new_name}[/green]")
            else:
                console.print(f"❌ Failed to copy profile")
                
        except Exception as e:
            console.print(f"❌ Error copying profile: {e}")
    
    asyncio.run(copy_profile())

@profiles.command()
@click.argument('name')
@click.confirmation_option(prompt='Are you sure you want to delete this profile?')
def delete(name):
    """Delete a user profile"""
    
    async def delete_profile():
        try:
            manager = ProfileManager()
            await manager.initialize()
            
            success = await manager.delete_profile(name)
            if success:
                console.print(f"✅ Profile deleted: [red]{name}[/red]")
            else:
                console.print(f"❌ Failed to delete profile (may be built-in)")
                
        except Exception as e:
            console.print(f"❌ Error deleting profile: {e}")
    
    asyncio.run(delete_profile())

@profiles.command()
@click.argument('name')
def set_default(name):
    """Set the default profile"""
    
    async def set_default_profile():
        try:
            manager = ProfileManager()
            await manager.initialize()
            
            success = manager.set_default_profile(name)
            if success:
                console.print(f"✅ Default profile set to: [cyan]{name}[/cyan]")
            else:
                console.print(f"❌ Profile not found: [red]{name}[/red]")
                
        except Exception as e:
            console.print(f"❌ Error setting default profile: {e}")
    
    asyncio.run(set_default_profile())

@profiles.command()
@click.argument('name')
@click.argument('yaml_file', type=click.Path(exists=True))
def create(name, yaml_file):
    """Create a new profile from YAML file"""
    
    async def create_profile():
        try:
            manager = ProfileManager()
            await manager.initialize()
            
            # Load YAML file
            yaml_path = Path(yaml_file)
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Override name
            data['name'] = name
            
            # Create profile
            profile = DownloadProfile.from_dict(data)
            
            success = await manager.create_profile(profile)
            if success:
                console.print(f"✅ Profile created: [green]{name}[/green]")
            else:
                console.print(f"❌ Failed to create profile")
                
        except Exception as e:
            console.print(f"❌ Error creating profile: {e}")
    
    asyncio.run(create_profile())

@profiles.command()
@click.argument('name')
@click.argument('yaml_file', type=click.Path())
def export(name, yaml_file):
    """Export a profile to YAML file"""
    
    async def export_profile():
        try:
            manager = ProfileManager()
            await manager.initialize()
            
            profile = manager.get_profile(name)
            if not profile:
                console.print(f"❌ Profile not found: [red]{name}[/red]")
                return
            
            # Export to YAML
            yaml_path = Path(yaml_file)
            profile.to_yaml(yaml_path)
            
            console.print(f"✅ Profile exported to: [cyan]{yaml_path}[/cyan]")
            
        except Exception as e:
            console.print(f"❌ Error exporting profile: {e}")
    
    asyncio.run(export_profile())

if __name__ == '__main__':
    profiles()
