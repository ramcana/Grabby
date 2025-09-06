#!/usr/bin/env python3
"""
Grabby - Universal Video Downloader
Main entry point for the application
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from cli.main import cli

if __name__ == '__main__':
    cli()
