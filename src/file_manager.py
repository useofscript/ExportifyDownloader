"""
File Manager for organizing downloaded music.
Handles folder creation, file naming, and path management.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, List, Tuple
import re


class FileManager:
    """
    Manages file operations for the music downloader.
    
    Responsibilities:
    - Create folder structure (Artist/Album/)
    - Handle file naming and conflicts
    - Check for existing files
    - Manage album art files
    - Manage LRC files
    """
    
    def __init__(self, base_output_dir: str = "~/Music"):
        """
        Initialize file manager.
        
        Args:
            base_output_dir: Base output directory (default: ~/Music)
        """
        self.base_output_dir = Path(os.path.expanduser(base_output_dir))
        
        # Create base directory if it doesn't exist
        self.base_output_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def base_dir(self) -> Path:
        """Get base output directory."""
        return self.base_output_dir
    
    def get_album_folder(self, artist: str, album: str) -> Path:
        """
        Get the album folder path.
        
        Args:
            artist: Artist name
            album: Album name
            
        Returns:
            Path to album folder
        """
        safe_artist = self._sanitize_folder_name(artist)
        safe_album = self._sanitize_folder_name(album)
        
        folder = self.base_output_dir / safe_artist / safe_album
        folder.mkdir(parents=True, exist_ok=True)
        
        return folder
    
    def get_track_path(self, artist: str, album: str, title: str, 
                      extension: str = ".m4a") -> Tuple[Path, bool]:
        """
        Get track file path, creating folders as needed.
        
        Args:
            artist: Artist name
            album: Album name
            title: Track title
            extension: File extension
            
        Returns:
            Tuple of (Path, exists) where exists indicates if file already exists
        """
        folder = self.get_album_folder(artist, album)
        
        # Create filename: "Artist - Title.ext"
        safe_artist = self._sanitize_filename(artist)
        safe_title = self._sanitize_filename(title)
        
        filename = f"{safe_artist} - {safe_title}{extension}"
        filepath = folder / filename
        
        # Handle filename conflicts
        if filepath.exists():
            filepath = self._handle_filename_conflict(filepath)
            return filepath, True
        
        return filepath, False
    
    def get_album_art_path(self, artist: str, album: str, 
                          is_track_specific: bool = False,
                          track_title: str = None) -> Path:
        """
        Get album art file path.
        
        Args:
            artist: Artist name
            album: Album name
            is_track_specific: If True, creates track-specific cover
            track_title: Track title for specific cover
            
        Returns:
            Path to album art file
        """
        safe_artist = self._sanitize_folder_name(artist)
        safe_album = self._sanitize_folder_name(album)
        
        folder = self.base_output_dir / safe_artist / safe_album
        
        if is_track_specific and track_title:
            safe_track = self._sanitize_filename(track_title)
            # Hidden file for track-specific cover
            return folder / f".{safe_track}.cover.jpg"
        else:
            # Album cover in .covers subfolder
            covers_folder = folder / ".covers"
            covers_folder.mkdir(parents=True, exist_ok=True)
            return covers_folder / "album.jpg"
    
    def get_lrc_path(self, artist: str, album: str, title: str) -> Path:
        """
        Get LRC lyrics file path.
        
        Args:
            artist: Artist name
            album: Album name
            title: Track title
            
        Returns:
            Path to LRC file
        """
        folder = self.get_album_folder(artist, album)
        
        safe_title = self._sanitize_filename(title)
        return folder / f"{safe_title}.lrc"
    
    def check_track_exists(self, artist: str, album: str, title: str,
                          extension: str = ".m4a") -> bool:
        """
        Check if track file already exists.
        
        Args:
            artist: Artist name
            album: Album name
            title: Track title
            extension: File extension
            
        Returns:
            True if file exists
        """
        folder = self.get_album_folder(artist, album)
        
        safe_artist = self._sanitize_filename(artist)
        safe_title = self._sanitize_filename(title)
        
        filename = f"{safe_artist} - {safe_title}{extension}"
        filepath = folder / filename
        
        return filepath.exists()
    
    def check_any_track_exists(self, artist: str, title: str,
                              extensions: List[str] = None) -> bool:
        """
        Check if track exists with any supported extension.
        
        Args:
            artist: Artist name
            title: Track title
            extensions: List of extensions to check
            
        Returns:
            True if file exists with any extension
        """
        if extensions is None:
            extensions = ['.m4a', '.mp3', '.flac', '.ogg', '.wav']
        
        safe_artist = self._sanitize_filename(artist)
        safe_title = self._sanitize_filename(title)
        
        base_name = f"{safe_artist} - {safe_title}"
        
        # Search in album folders
        for ext in extensions:
            # Check various possible locations
            potential_files = [
                self.base_output_dir / safe_artist / "*" / f"{base_name}{ext}",
                self.base_output_dir / safe_artist / f"{base_name}{ext}",
            ]
            
            for pattern in potential_files:
                matches = list(self.base_output_dir.glob(str(pattern).replace("*", "*")))
                if matches:
                    return True
        
        return False
    
    def move_file(self, source: Path, destination: Path,
                  create_folders: bool = True) -> Path:
        """
        Move file from source to destination.
        
        Args:
            source: Source file path
            destination: Destination file path
            create_folders: Create parent folders if needed
            
        Returns:
            New file path
        """
        if create_folders:
            destination.parent.mkdir(parents=True, exist_ok=True)
        
        if source == destination:
            return destination
        
        # If destination exists, handle conflict
        if destination.exists():
            destination = self._handle_filename_conflict(destination)
        
        shutil.move(str(source), str(destination))
        return destination
    
    def copy_file(self, source: Path, destination: Path,
                  create_folders: bool = True) -> Path:
        """
        Copy file from source to destination.
        
        Args:
            source: Source file path
            destination: Destination file path
            create_folders: Create parent folders if needed
            
        Returns:
            New file path
        """
        if create_folders:
            destination.parent.mkdir(parents=True, exist_ok=True)
        
        if destination.exists():
            destination = self._handle_filename_conflict(destination)
        
        shutil.copy2(str(source), str(destination))
        return destination
    
    def save_lrc_file(self, artist: str, album: str, title: str,
                     lyrics_content: str) -> Path:
        """
        Save LRC lyrics file.
        
        Args:
            artist: Artist name
            album: Album name
            title: Track title
            lyrics_content: LRC formatted lyrics
            
        Returns:
            Path to saved file
        """
        lrc_path = self.get_lrc_path(artist, album, title)
        
        with open(lrc_path, 'w', encoding='utf-8') as f:
            f.write(lyrics_content)
        
        return lrc_path
    
    def get_folder_size(self, path: Path = None) -> int:
        """
        Get total size of folder in bytes.
        
        Args:
            path: Folder path (defaults to base output dir)
            
        Returns:
            Total size in bytes
        """
        if path is None:
            path = self.base_output_dir
        
        total = 0
        for entry in path.rglob('*'):
            if entry.is_file():
                total += entry.stat().st_size
        
        return total
    
    def format_size(self, bytes: int) -> str:
        """
        Format bytes to human readable size.
        
        Args:
            bytes: Size in bytes
            
        Returns:
            Formatted string (e.g., "1.5 MB")
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024
        
        return f"{bytes:.2f} PB"
    
    def list_tracks(self, artist: str = None, album: str = None) -> List[Path]:
        """
        List tracks in folder structure.
        
        Args:
            artist: Optional artist filter
            album: Optional album filter
            
        Returns:
            List of track file paths
        """
        audio_extensions = ['.m4a', '.mp3', '.flac', '.ogg', '.wav']
        
        if artist and album:
            folder = self.base_output_dir / artist / album
        elif artist:
            folder = self.base_output_dir / artist
        else:
            folder = self.base_output_dir
        
        tracks = []
        for ext in audio_extensions:
            tracks.extend(folder.rglob(f"*{ext}"))
        
        return sorted(tracks)
    
    def cleanup_empty_folders(self) -> int:
        """
        Remove empty folders from structure.
        
        Returns:
            Number of folders removed
        """
        removed = 0
        
        for folder in sorted(self.base_output_dir.rglob('*'), reverse=True):
            if folder.is_dir():
                # Only remove if not base output dir
                if folder != self.base_output_dir and not any(folder.iterdir()):
                    folder.rmdir()
                    removed += 1
        
        return removed
    
    def _sanitize_folder_name(self, name: str) -> str:
        """
        Sanitize folder name.
        
        Args:
            name: Original name
            
        Returns:
            Sanitized folder name
        """
        if not name:
            return "Unknown"
        
        # Characters to remove or replace in folders
        invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
        sanitized = re.sub(invalid_chars, '', name)
        
        # Replace certain characters with safe alternatives
        replacements = {
            '*': '_',
            '?': '_',
        }
        for old, new in replacements.items():
            sanitized = sanitized.replace(old, new)
        
        # Limit length
        max_length = 100
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length].strip()
        
        return sanitized.strip() if sanitized else "Unknown"
    
    def _sanitize_filename(self, name: str) -> str:
        """
        Sanitize filename.
        
        Args:
            name: Original name
            
        Returns:
            Sanitized filename
        """
        if not name:
            return "Unknown"
        
        # Replace with safe alternatives first (before regex strips them)
        safe_replacements = {
            '/': ' and ',
            '\\': ' - ',
            ':': ' - ',
            '*': '_',
            '?': '',
            '"': "'",
            '<': '',
            '>': '',
            '|': ' - ',
        }
        
        sanitized = name
        for old, new in safe_replacements.items():
            sanitized = sanitized.replace(old, new)
        
        # Remove any remaining invalid characters
        invalid_chars = r'[\x00-\x1f]'
        sanitized = re.sub(invalid_chars, '', sanitized)
        
        # Limit length
        max_length = 80
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length].strip()
        
        # Remove trailing spaces and dots
        sanitized = sanitized.rstrip(' .')
        
        return sanitized.strip() if sanitized else "Unknown"
    
    def _handle_filename_conflict(self, filepath: Path) -> Path:
        """
        Handle filename conflict by adding number suffix.
        
        Args:
            filepath: Original filepath
            
        Returns:
            New filepath with unique name
        """
        if not filepath.exists():
            return filepath
        
        folder = filepath.parent
        stem = filepath.stem
        extension = filepath.suffix
        
        # Pattern: "Artist - Title (1).ext"
        counter = 1
        while True:
            new_name = f"{stem} ({counter}){extension}"
            new_path = folder / new_name
            
            if not new_path.exists():
                return new_path
            
            counter += 1
            
            # Safety limit
            if counter > 999:
                # Use timestamp instead
                import time
                timestamp = int(time.time())
                new_name = f"{stem}_{timestamp}{extension}"
                new_path = folder / new_name
                return new_path


# Convenience functions
def get_file_manager(base_dir: str = "~/Music") -> FileManager:
    """
    Create FileManager instance.
    
    Args:
        base_dir: Base output directory
        
    Returns:
        FileManager instance
    """
    return FileManager(base_dir)

