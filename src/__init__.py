"""
Exportify YouTube Downloader Package
"""

__version__ = "1.0.0"
__author__ = "Exportify Downloader Team"

from src.csv_parser import parse_csv, parse_csv_string, ExportifyCSVParser
from src.youtube_downloader import YouTubeDownloader, get_downloader
from src.file_manager import FileManager, get_file_manager
from src.metadata_handler import MetadataHandler, get_metadata_handler
from src.config import Config, get_config

__all__ = [
    # CSV Parser
    'parse_csv',
    'parse_csv_string',
    'ExportifyCSVParser',
    # YouTube Downloader
    'YouTubeDownloader',
    'get_downloader',
    # File Manager
    'FileManager',
    'get_file_manager',
    # Metadata Handler
    'MetadataHandler',
    'get_metadata_handler',
    # Config
    'Config',
    'get_config',
]

