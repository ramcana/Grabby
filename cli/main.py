"""
Simple CLI interface - Quick wins and immediate usability
"""
import asyncio
import sys
from pathlib import Path
from typing import List, Optional
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from backend.core.unified_downloader import create_downloader, UnifiedDownloader
from backend.core.downloader import DownloadOptions, DownloadProgress, DownloadStatus
from config.profile_manager import ProfileManager

console = Console()

class CLIProgressTracker:
    """Tracks and displays download progress in the CLI"""
    
    def __init__(self):
        self.progress_bars = {}
        self.progress = None
        
    def start_progress_display(self):
        """Initialize the progress display"""
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.fields[filename]}", justify="left"),
            BarColumn(bar_width=None),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
            expand=True
        )
        self.progress.start()
        
    def stop_progress_display(self):
        """Stop the progress display"""
        if self.progress:
            self.progress.stop()
            self.progress = None
            
    def update_progress(self, download_progress: DownloadProgress):
        """Update progress for a download"""
        if not self.progress:
            return
            
        url = download_progress.url
        
        if url not in self.progress_bars:
            # Create new progress bar
            task_id = self.progress.add_task(
                "download",
                filename=download_progress.filename or url[:50] + "...",
                total=100
            )
            self.progress_bars[url] = task_id
        else:
            task_id = self.progress_bars[url]
            
        # Update the progress bar
        if download_progress.status == DownloadStatus.DOWNLOADING:
            self.progress.update(
                task_id,
                completed=download_progress.progress_percent,
                filename=download_progress.filename or url[:50] + "..."
            )
        elif download_progress.status == DownloadStatus.COMPLETED:
            self.progress.update(task_id, completed=100)
            self.progress.update(task_id, filename=f"✓ {download_progress.filename}")
        elif download_progress.status == DownloadStatus.FAILED:
            self.progress.update(task_id, filename=f"✗ {download_progress.filename or 'Failed'}")

@click.group()
@click.version_option(version="1.0.0", prog_name="grabby")
def cli():
    """
    🎬 Grabby - Universal Video Downloader
    
    Download videos from YouTube, TikTok, Instagram, and more!
    """
    pass

@cli.command()
@click.argument('urls', nargs=-1, required=True)
@click.option('--output', '-o', default='./downloads', help='Output directory')
@click.option('--format', '-f', default='best[height<=1080]', help='Video format')
@click.option('--audio-only', '-a', is_flag=True, help='Extract audio only')
@click.option('--concurrent', '-c', default=3, help='Concurrent downloads')
@click.option('--quality', '-q', type=click.Choice(['best', 'worst', '720p', '1080p']), default='best', help='Quality preset')
@click.option('--engine', '-e', type=click.Choice(['auto', 'yt-dlp', 'multi']), default='multi', help='Download engine')
@click.option('--show-engines', is_flag=True, help='Show optimal engine for each URL')
@click.option('--profile', '-p', help='Use download profile')
def download(urls, output, format, audio_only, concurrent, quality, engine, show_engines, profile):
    """Download videos from URLs using multi-engine system"""
    
    # Quality presets
    quality_map = {
        'best': 'best[height<=1080]',
        'worst': 'worst',
        '720p': 'best[height<=720]',
        '1080p': 'best[height<=1080]'
    }
    
    if quality in quality_map:
        format = quality_map[quality]
    
    use_multi_engine = engine in ['auto', 'multi']
    
    options = DownloadOptions(
        output_path=output,
        format_selector=format,
        extract_audio=audio_only,
        concurrent_downloads=concurrent
    )
    
    asyncio.run(download_urls(urls, options, use_multi_engine, show_engines, profile))

@cli.command()
@click.argument('url')
def info(url):
    """Get video information without downloading"""
    
    async def get_info():
        try:
            downloader = UniversalDownloader()
            console.print(f"🔍 Extracting info for: [cyan]{url}[/cyan]")
            
            with console.status("[bold green]Fetching video information..."):
                video_info = await downloader.get_video_info(url)
            
            # Display video information
            show_video_info(video_info)
            
        except Exception as e:
            console.print(f"❌ Error extracting info: {e}")
    
    asyncio.run(get_info())

@cli.command()
@click.option('--output', '-o', default='./downloads', help='Downloads directory to check')
def status(output):
    """Show download status and history"""
    
    downloads_path = Path(output)
    if not downloads_path.exists():
        console.print(f"❌ Downloads directory not found: {output}")
        return
    
    # Count files in downloads directory
    video_files = list(downloads_path.glob('*.mp4')) + list(downloads_path.glob('*.mkv')) + \
                 list(downloads_path.glob('*.webm')) + list(downloads_path.glob('*.avi'))
    audio_files = list(downloads_path.glob('*.mp3')) + list(downloads_path.glob('*.m4a')) + \
                 list(downloads_path.glob('*.wav'))
    
    table = Table(title="📊 Download Status")
    table.add_column("Type", style="cyan")
    table.add_column("Count", style="green")
    table.add_column("Total Size", style="yellow")
    
    def get_total_size(files):
        return sum(f.stat().st_size for f in files if f.exists())
    
    def format_size(size_bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    table.add_row("Video Files", str(len(video_files)), format_size(get_total_size(video_files)))
    table.add_row("Audio Files", str(len(audio_files)), format_size(get_total_size(audio_files)))
    table.add_row("Total Files", str(len(video_files) + len(audio_files)), 
                  format_size(get_total_size(video_files + audio_files)))
    
    console.print(table)
    
    # Show recent files
    if video_files or audio_files:
        all_files = sorted(video_files + audio_files, key=lambda x: x.stat().st_mtime, reverse=True)
        recent_files = all_files[:5]
        
        console.print("\n📁 Recent Downloads:")
        for file in recent_files:
            size = format_size(file.stat().st_size)
            console.print(f"  • [cyan]{file.name}[/cyan] ([yellow]{size}[/yellow])")

def show_video_info(info):
    """Display video information in a formatted table"""
    
    table = Table(title="📹 Video Information")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    # Basic info
    table.add_row("Title", info.get('title', 'Unknown'))
    table.add_row("Uploader", info.get('uploader', 'Unknown'))
    table.add_row("Duration", str(info.get('duration', 'Unknown')) + " seconds")
    table.add_row("View Count", str(info.get('view_count', 'Unknown')))
    table.add_row("Upload Date", info.get('upload_date', 'Unknown'))
    
    # Technical info
    if 'formats' in info and info['formats']:
        best_format = info['formats'][-1]
        table.add_row("Best Quality", f"{best_format.get('height', 'Unknown')}p")
        table.add_row("Video Codec", best_format.get('vcodec', 'Unknown'))
        table.add_row("Audio Codec", best_format.get('acodec', 'Unknown'))
    
    console.print(table)
    
    # Description
    if info.get('description'):
        description = info['description'][:200] + "..." if len(info['description']) > 200 else info['description']
        console.print(f"\n📝 Description:\n[italic]{description}[/italic]")

async def download_urls(urls: List[str], options: DownloadOptions, use_multi_engine: bool = True, show_engines: bool = False, profile_name: Optional[str] = None):
    """Download multiple URLs with progress tracking using unified downloader"""
    tracker = CLIProgressTracker()
    
    # Initialize profile manager if profile is specified
    profile_manager = None
    if profile_name:
        profile_manager = ProfileManager()
        await profile_manager.initialize()
        
        # Check if profile exists
        if not profile_manager.get_profile(profile_name):
            console.print(f"❌ Profile not found: [red]{profile_name}[/red]")
            available_profiles = profile_manager.list_profiles()
            if available_profiles:
                console.print(f"Available profiles: {', '.join(available_profiles)}")
            return
    
    # Create unified downloader
    downloader = create_downloader(
        use_multi_engine=use_multi_engine,
        output_path=options.output_path,
        concurrent_downloads=options.concurrent_downloads,
        profile_manager=profile_manager
    )
    
    await downloader.initialize()
    downloader.add_progress_callback(tracker.update_progress)
    
    engine_type = "Multi-Engine" if use_multi_engine else "yt-dlp"
    console.print(f"\n🎬 Starting downloads to: [bold cyan]{options.output_path}[/bold cyan]")
    console.print(f"🔧 Engine: [bold magenta]{engine_type}[/bold magenta]")
    console.print(f"📊 Format: [bold yellow]{options.format_selector}[/bold yellow]")
    console.print(f"🔄 Concurrent downloads: [bold green]{options.concurrent_downloads}[/bold green]\n")
    
    # Show optimal engines if requested
    if show_engines and use_multi_engine:
        console.print("🔍 [bold]Optimal engines for URLs:[/bold]")
        for url in urls:
            engine = await downloader.get_optimal_engine(url)
            console.print(f"  • {url} → [cyan]{engine}[/cyan]")
        console.print()
    
    tracker.start_progress_display()
    
    # Set profile if specified
    if profile_name:
        success = await downloader.set_profile(profile_name)
        if success:
            console.print(f"📋 Using profile: [bold cyan]{profile_name}[/bold cyan]")
        else:
            console.print(f"⚠️ Failed to apply profile: [yellow]{profile_name}[/yellow]")
    
    try:
        results = await downloader.download_batch(list(urls), profile_name=profile_name)
        tracker.stop_progress_display()
        
        # Show summary
        show_download_summary(results)
        
        # Show engine status if multi-engine
        if use_multi_engine:
            status = downloader.get_engine_status()
            console.print(f"\n📊 [bold]Engine Status:[/bold] {len(status.get('available_engines', []))} engines available")
        
    except KeyboardInterrupt:
        tracker.stop_progress_display()
        console.print("\n❌ Downloads cancelled by user")
        # Cancel all active downloads
        for url in urls:
            await downloader.cancel_download(url)
    except Exception as e:
        tracker.stop_progress_display()
        console.print(f"\n❌ Error: {e}")

def show_download_summary(results: List[DownloadProgress]):
    """Show a summary of download results"""
    
    successful = [r for r in results if r.status == DownloadStatus.COMPLETED]
    failed = [r for r in results if r.status == DownloadStatus.FAILED]
    
    console.print("\n" + "="*50)
    console.print("📊 Download Summary")
    console.print("="*50)
    
    if successful:
        console.print(f"✅ Successful: [bold green]{len(successful)}[/bold green]")
        for result in successful:
            console.print(f"  • [green]{result.filename}[/green]")
    
    if failed:
        console.print(f"\n❌ Failed: [bold red]{len(failed)}[/bold red]")
        for result in failed:
            console.print(f"  • [red]{result.url}[/red]")
            if result.error_message:
                console.print(f"    Error: [dim]{result.error_message}[/dim]")
    
    console.print(f"\n🎯 Total: {len(results)} downloads")

# Quick preset commands
@cli.command()
@click.argument('urls', nargs=-1, required=True)
@click.option('--output', '-o', default='./downloads')
def audio(urls, output):
    """Quick command to download audio only"""
    ctx = click.get_current_context()
    ctx.invoke(download, urls=urls, output=output, profile='audio_only')

@cli.command()
@click.argument('urls', nargs=-1, required=True)
@click.option('--output', '-o', default='./downloads')
def hd(urls, output):
    """Quick command to download in HD (1080p)"""
    ctx = click.get_current_context()
    ctx.invoke(download, urls=urls, output=output, profile='high_quality')

# Profile management commands
from .profiles import profiles
cli.add_command(profiles)

if __name__ == '__main__':
    cli()
