"""
Configuration settings for Exportify YouTube Downloader.
Handles all configuration with environment variable support.
"""

import os
import json
from pathlib import Path
from typing import Optional


class Config:
    """Configuration manager with environment variable support."""
    
    # Default settings
    DEFAULT_OUTPUT_DIR = "~/Music"
    DEFAULT_PARALLEL_DOWNLOADS = 4
    DEFAULT_SKIP_EXISTING = True
    DEFAULT_CREATE_LRC = True
    DEFAULT_ALBUM_ART_SIZE = 1200
    DEFAULT_AUDIO_FORMAT = "best"  # yt-dlp auto-selects best
    DEFAULT_VERBOSE = False
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Optional path to config JSON file
        """
        self._config_file = config_path
        self._settings = self._load_defaults()
        
        if config_path and os.path.exists(config_path):
            self._load_from_file(config_path)
        
        self._apply_env_variables()
    
    def _load_defaults(self) -> dict:
        """Load default configuration."""
        return {
            "output_dir": self.DEFAULT_OUTPUT_DIR,
            "parallel_downloads": self.DEFAULT_PARALLEL_DOWNLOADS,
            "skip_existing": self.DEFAULT_SKIP_EXISTING,
            "create_lrc": self.DEFAULT_CREATE_LRC,
            "album_art_size": self.DEFAULT_ALBUM_ART_SIZE,
            "audio_format": self.DEFAULT_AUDIO_FORMAT,
            "verbose": self.DEFAULT_VERBOSE,
            "download_timeout": 300,  # seconds
            "max_retries": 3,
            "file_naming_pattern": "{artist} - {title}",
            "folder_structure": "{artist}/{album}/",
        }
    
    def _load_from_file(self, config_path: str) -> None:
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                self._settings.update(file_config)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load config file {config_path}: {e}")
    
    def _apply_env_variables(self) -> None:
        """Apply environment variable overrides."""
        env_mappings = {
            "EXPORTIFY_OUTPUT_DIR": ("output_dir", str),
            "EXPORTIFY_PARALLEL": ("parallel_downloads", int),
            "EXPORTIFY_SKIP_EXISTING": ("skip_existing", lambda x: x.lower() == "true"),
            "EXPORTIFY_CREATE_LRC": ("create_lrc", lambda x: x.lower() == "true"),
            "EXPORTIFY_ALBUM_ART_SIZE": ("album_art_size", int),
            "EXPORTIFY_VERBOSE": ("verbose", lambda x: x.lower() == "true"),
            "EXPORTIFY_TIMEOUT": ("download_timeout", int),
            "EXPORTIFY_RETRIES": ("max_retries", int),
        }
        
        for env_var, (key, converter) in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                try:
                    self._settings[key] = converter(value)
                except (ValueError, TypeError) as e:
                    print(f"Warning: Invalid value for {env_var}: {e}")
    
    @property
    def output_dir(self) -> Path:
        """Get expanded output directory path."""
        return Path(os.path.expanduser(self._settings["output_dir"]))
    
    @output_dir.setter
    def output_dir(self, value: str) -> None:
        """Set output directory."""
        self._settings["output_dir"] = value
    
    @property
    def parallel_downloads(self) -> int:
        """Get number of parallel downloads."""
        return int(self._settings["parallel_downloads"])
    
    @parallel_downloads.setter
    def parallel_downloads(self, value: int) -> None:
        """Set number of parallel downloads."""
        self._settings["parallel_downloads"] = value
    
    @property
    def skip_existing(self) -> bool:
        """Get skip existing files setting."""
        return bool(self._settings["skip_existing"])
    
    @skip_existing.setter
    def skip_existing(self, value: bool) -> None:
        """Set skip existing files setting."""
        self._settings["skip_existing"] = value
    
    @property
    def create_lrc(self) -> bool:
        """Get create LRC files setting."""
        return bool(self._settings["create_lrc"])
    
    @create_lrc.setter
    def create_lrc(self, value: bool) -> None:
        """Set create LRC files setting."""
        self._settings["create_lrc"] = value
    
    @property
    def album_art_size(self) -> int:
        """Get max album art size (pixels)."""
        return int(self._settings["album_art_size"])
    
    @property
    def audio_format(self) -> str:
        """Get audio format."""
        return self._settings["audio_format"]
    
    @property
    def verbose(self) -> bool:
        """Get verbose mode setting."""
        return bool(self._settings["verbose"])
    
    @verbose.setter
    def verbose(self, value: bool) -> None:
        """Set verbose mode setting."""
        self._settings["verbose"] = value
    
    @property
    def download_timeout(self) -> int:
        """Get download timeout in seconds."""
        return int(self._settings["download_timeout"])
    
    @property
    def max_retries(self) -> int:
        """Get max retry attempts."""
        return int(self._settings["max_retries"])
    
    @property
    def file_naming_pattern(self) -> str:
        """Get file naming pattern."""
        return self._settings["file_naming_pattern"]
    
    @property
    def folder_structure(self) -> str:
        """Get folder structure pattern."""
        return self._settings["folder_structure"]
    
    def get_yt_dlp_options(self) -> dict:
        """
        Get yt-dlp options based on configuration.
        
        Returns:
            Dictionary of yt-dlp options
        """
        return {
            'format': self.audio_format,  # 'best' for highest quality
            'outtmpl': '%(title)s',  # Temporary template, overridden in downloader
            'writethumbnail': True,  # Download album art
            'writelinks': False,
            'writeinfojson': False,
            'writedescription': False,
            'noplaylist': True,  # Download single videos
            'nocheckcertificate': False,
            'no_warnings': False,
            'quiet': not self.verbose,
            'no_color': False,
            'verbose': self.verbose,
            'progress': True,
            'concurrent-fragments': 4,
            'retries': self.max_retries,
            'timeout': self.download_timeout,
            # Audio extraction options
            'extractaudio': True,
            'audiocodec': 'best',  # Let yt-dlp choose best codec
            # Post-processing options
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'm4a',  # m4a/aac usually best quality
                    'preferredquality': '0',  # 0 = best quality
                },
                {
                    'key': 'EmbedThumbnail',
                },
                # Metadata will be added separately
            ],
        }
    
    def get_track_path(self, artist: str, album: str, title: str, ext: str = ".m4a") -> Path:
        """
        Generate track file path.
        
        Args:
            artist: Artist name
            album: Album name
            title: Track title
            ext: File extension
            
        Returns:
            Full path to track file
        """
        # Sanitize folder and file names
        safe_artist = self._sanitize_name(artist)
        safe_album = self._sanitize_name(album)
        safe_title = self._sanitize_name(title)
        
        folder = self.output_dir / safe_artist / safe_album
        filename = f"{safe_artist} - {safe_title}{ext}"
        
        return folder / filename
    
    def get_album_art_path(self, artist: str, album: str, track_title: str = None) -> Path:
        """
        Generate album art file path.
        
        Args:
            artist: Artist name
            album: Album name
            track_title: Optional track-specific cover
            
        Returns:
            Path to album art file
        """
        safe_artist = self._sanitize_name(artist)
        safe_album = self._sanitize_name(album)
        
        if track_title:
            # Track-specific cover
            safe_track = self._sanitize_name(track_title)
            folder = self.output_dir / safe_artist / safe_album
            return folder / f".{safe_track}.cover.jpg"
        else:
            # Album cover
            folder = self.output_dir / safe_artist / safe_album / ".covers"
            return folder / "album.jpg"
    
    def get_lrc_path(self, artist: str, album: str, title: str) -> Path:
        """
        Generate LRC lyrics file path.
        
        Args:
            artist: Artist name
            album: Album name
            title: Track title
            
        Returns:
            Path to LRC file
        """
        safe_artist = self._sanitize_name(artist)
        safe_album = self._sanitize_name(album)
        safe_title = self._sanitize_name(title)
        
        folder = self.output_dir / safe_artist / safe_album
        return folder / f"{safe_title}.lrc"
    
    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize folder/file name by removing invalid characters.
        
        Args:
            name: Original name
            
        Returns:
            Sanitized name safe for filesystem
        """
        if not name:
            return "Unknown"
        
        # Characters to remove
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\0']
        
        sanitized = name
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Limit length
        max_length = 100
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        # Strip whitespace
        sanitized = sanitized.strip()
        
        # Ensure not empty
        if not sanitized:
            sanitized = "Unknown"
        
        return sanitized
    
    def save(self, config_path: str = None) -> None:
        """
        Save current configuration to file.
        
        Args:
            config_path: Path to save config (uses default if not specified)
        """
        save_path = config_path or self._config_file
        
        if not save_path:
            save_path = os.path.expanduser("~/.config/exportify_downloader/config.json")
        
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(self._settings, f, indent=4, ensure_ascii=False)


# Global config instance
_config: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """
    Get global configuration instance.
    
    Args:
        config_path: Optional config file path
        
    Returns:
        Config instance
    """
    global _config
    
    if _config is None:
        _config = Config(config_path)
    
    return _config


def reset_config() -> None:
    """Reset global configuration (for testing)."""
    global _config
    _config = None

