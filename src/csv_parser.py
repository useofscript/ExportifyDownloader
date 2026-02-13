"""
CSV Parser for Exportify Spotify playlist exports.
Parses CSV files containing Track Name, Artist Name, Album Name, Added By, Added At columns.
"""

import csv
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any


@dataclass
class Track:
    """Represents a single track from the CSV."""
    track_name: str
    artist_name: str
    album_name: str
    added_by: str = ""
    added_at: str = ""
    duration: str = ""  # Optional, if present in CSV
    track_number: str = ""  # Optional, if present in CSV
    album_artist: str = ""  # Album artist (may differ from track artist)
    album_release_date: str = ""  # Release date from Exportify
    album_image_url: str = ""  # Album cover URL from Spotify
    disc_number: str = ""  # Disc number
    isrc: str = ""  # International Standard Recording Code
    popularity: str = ""  # Spotify popularity score
    explicit: str = ""  # Explicit flag
    
    def to_dict(self) -> Dict[str, str]:
        """Convert track to dictionary."""
        return {
            "track_name": self.track_name,
            "artist_name": self.artist_name,
            "album_name": self.album_name,
            "added_by": self.added_by,
            "added_at": self.added_at,
            "duration": self.duration,
            "track_number": self.track_number,
            "album_artist": self.album_artist,
            "album_release_date": self.album_release_date,
            "album_image_url": self.album_image_url,
            "disc_number": self.disc_number,
            "isrc": self.isrc,
            "popularity": self.popularity,
            "explicit": self.explicit,
        }
    
    def get_search_query(self) -> str:
        """
        Generate YouTube search query from track info.
        
        Returns:
            Search query string
        """
        # Format: "Artist Name - Track Name" for better search results
        return f"{self.artist_name} - {self.track_name}"
    
    def get_download_filename(self) -> str:
        """
        Generate filename for downloaded file.
        
        Returns:
            Safe filename for the track
        """
        # Format: "Artist - Title"
        safe_artist = self._sanitize_filename(self.artist_name)
        safe_title = self._sanitize_filename(self.track_name)
        return f"{safe_artist} - {safe_title}"
    
    def _sanitize_filename(self, name: str) -> str:
        """Remove characters invalid in filenames."""
        if not name:
            return "Unknown"
        
        # Remove or replace invalid characters
        invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
        sanitized = re.sub(invalid_chars, '', name)
        
        # Limit length
        max_length = 80
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length].strip()
        
        return sanitized.strip() if sanitized else "Unknown"


@dataclass 
class Playlist:
    """Represents a parsed playlist from CSV."""
    name: str
    tracks: List[Track] = field(default_factory=list)
    source_file: str = ""
    
    def __len__(self) -> int:
        """Return number of tracks."""
        return len(self.tracks)
    
    def get_artists(self) -> List[str]:
        """Get unique list of artists."""
        return list(set(t.artist_name for t in self.tracks if t.artist_name))
    
    def get_albums(self) -> List[str]:
        """Get unique list of albums."""
        return list(set(t.album_name for t in self.tracks if t.album_name))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get playlist statistics."""
        return {
            "total_tracks": len(self.tracks),
            "unique_artists": len(self.get_artists()),
            "unique_albums": len(self.get_albums()),
        }


class CSVParseError(Exception):
    """Custom exception for CSV parsing errors."""
    pass


class ExportifyCSVParser:
    """
    Parser for Exportify CSV format.
    
    Exportify CSV format typically includes:
    - Track Name
    - Artist Name  
    - Album Name
    - Added By (optional)
    - Added At (optional)
    """
    
    # Standard column names in Exportify exports
    STANDARD_COLUMNS = [
        'track name',
        'artist name', 
        'album name',
        'added by',
        'added at',
    ]
    
    # Alternative column names (case insensitive variations)
    COLUMN_VARIATIONS = {
        'track name': ['track name', 'trackname', 'track', 'title', 'song'],
        'artist name': ['artist name', 'artist name(s)', 'artistname', 'artist', 'performer'],
        'album name': ['album name', 'albumname', 'album', 'collection'],
        'album artist': ['album artist name(s)', 'album artist', 'albumartist'],
        'added by': ['added by', 'addedby', 'user'],
        'added at': ['added at', 'addedat', 'date added'],
        'track number': ['track number', 'tracknumber', 'track #', 'track no'],
        'disc number': ['disc number', 'discnumber', 'disc #', 'disc no'],
        'duration': ['track duration (ms)', 'duration', 'duration (ms)', 'length'],
        'album release date': ['album release date', 'release date', 'date', 'year'],
        'album image url': ['album image url', 'album art', 'cover url', 'image url'],
        'isrc': ['isrc'],
        'popularity': ['popularity'],
        'explicit': ['explicit'],
    }
    
    def __init__(self, encoding: str = 'utf-8'):
        """
        Initialize parser.
        
        Args:
            encoding: File encoding (default: utf-8)
        """
        self.encoding = encoding
    
    def parse(self, file_path: str) -> Playlist:
        """
        Parse an Exportify CSV file.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            Playlist object with parsed tracks
            
        Raises:
            CSVParseError: If file cannot be parsed
            FileNotFoundError: If file doesn't exist
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"CSV file not found: {file_path}")
        
        playlist_name = Path(file_path).stem
        
        try:
            with open(file_path, 'r', encoding=self.encoding, errors='replace') as f:
                content = f.read()
            
            # Try to detect and handle different line endings
            content = content.replace('\r\n', '\n').replace('\r', '\n')
            
            # Parse CSV content
            reader = csv.reader(content.splitlines(), delimiter=',')
            
            # Get header and normalize
            rows = list(reader)
            if not rows:
                raise CSVParseError("Empty CSV file")
            
            header = self._normalize_header(rows[0])
            
            # Validate required columns
            self._validate_header(header)
            
            # Parse tracks
            tracks = []
            for row_num, row in enumerate(rows[1:], start=2):
                if not row or len(row) < 3:
                    continue  # Skip empty or malformed rows
                
                try:
                    track = self._parse_row(header, row, row_num)
                    if track:
                        tracks.append(track)
                except Exception as e:
                    # Log warning but continue with other tracks
                    print(f"Warning: Could not parse row {row_num}: {e}")
                    continue
            
            if not tracks:
                raise CSVParseError("No valid tracks found in CSV")
            
            return Playlist(
                name=playlist_name,
                tracks=tracks,
                source_file=os.path.abspath(file_path),
            )
            
        except csv.Error as e:
            raise CSVParseError(f"CSV parsing error: {e}")
        except IOError as e:
            raise CSVParseError(f"File read error: {e}")
    
    def parse_string(self, content: str, playlist_name: str = "Imported Playlist") -> Playlist:
        """
        Parse CSV content from string.
        
        Args:
            content: CSV content as string
            playlist_name: Name for the playlist
            
        Returns:
            Playlist object
        """
        try:
            content = content.replace('\r\n', '\n').replace('\r', '\n')
            reader = csv.reader(content.splitlines(), delimiter=',')
            rows = list(reader)
            
            if not rows:
                raise CSVParseError("Empty CSV content")
            
            header = self._normalize_header(rows[0])
            self._validate_header(header)
            
            tracks = []
            for row_num, row in enumerate(rows[1:], start=2):
                if not row or len(row) < 3:
                    continue
                
                try:
                    track = self._parse_row(header, row, row_num)
                    if track:
                        tracks.append(track)
                except Exception as e:
                    print(f"Warning: Could not parse row {row_num}: {e}")
                    continue
            
            return Playlist(
                name=playlist_name,
                tracks=tracks,
                source_file="",
            )
            
        except csv.Error as e:
            raise CSVParseError(f"CSV parsing error: {e}")
    
    def _normalize_header(self, header: List[str]) -> List[str]:
        """
        Normalize CSV header to standard column names.
        
        Args:
            header: Raw header row
            
        Returns:
            Normalized header
        """
        normalized = []
        for col in header:
            col_lower = col.strip().lower()
            
            # Match to standard column name
            matched = False
            for std_col, variations in self.COLUMN_VARIATIONS.items():
                if col_lower in variations:
                    normalized.append(std_col)
                    matched = True
                    break
            
            if not matched:
                # Keep original if no match
                normalized.append(col.strip().lower())
        
        return normalized
    
    def _validate_header(self, header: List[str]) -> None:
        """
        Validate that required columns exist.
        
        Args:
            header: Normalized header
            
        Raises:
            CSVParseError: If required columns missing
        """
        required = ['track name', 'artist name', 'album name']
        
        missing = []
        for req in required:
            if req not in header:
                missing.append(req)
        
        if missing:
            raise CSVParseError(
                f"Missing required columns: {', '.join(missing)}. "
                f"Found columns: {', '.join(header)}"
            )
    
    def _parse_row(self, header: List[str], row: List[str], row_num: int) -> Optional[Track]:
        """
        Parse a single CSV row into a Track.
        
        Args:
            header: Normalized header
            row: CSV row
            row_num: Row number for error messages
            
        Returns:
            Track object or None if invalid
        """
        # Build field mapping
        field_map = {}
        for i, col in enumerate(header):
            if i < len(row):
                # Handle quoted fields with commas
                value = row[i].strip()
                # Remove surrounding quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                field_map[col] = value
            else:
                field_map[col] = ""
        
        # Extract required fields
        track_name = field_map.get('track name', '').strip()
        artist_name = field_map.get('artist name', '').strip()
        album_name = field_map.get('album name', '').strip()
        
        # Validate required fields
        if not track_name or not artist_name or not album_name:
            return None
        
        return Track(
            track_name=track_name,
            artist_name=artist_name,
            album_name=album_name,
            added_by=field_map.get('added by', '').strip(),
            added_at=field_map.get('added at', '').strip(),
            track_number=field_map.get('track number', '').strip(),
            disc_number=field_map.get('disc number', '').strip(),
            duration=field_map.get('duration', '').strip(),
            album_artist=field_map.get('album artist', '').strip(),
            album_release_date=field_map.get('album release date', '').strip(),
            album_image_url=field_map.get('album image url', '').strip(),
            isrc=field_map.get('isrc', '').strip(),
            popularity=field_map.get('popularity', '').strip(),
            explicit=field_map.get('explicit', '').strip(),
        )
    
    def get_sample_csv(self) -> str:
        """
        Generate sample Exportify CSV for testing.
        
        Returns:
            Sample CSV content
        """
        return '''Track Name,Artist Name,Album Name,Added By,Added At
"Shape of You","Ed Sheeran","÷ (Divide)","user1","2024-01-15"
"Blinding Lights","The Weeknd","After Hours","user1","2024-01-16"
"drivers license","Olivia Rodrigo","SOUR","user1","2024-01-17"
"Stay","The Kid LAROI","F*CK LOVE 3: OVER YOU","user1","2024-01-18"
"Good 4 U","Olivia Rodrigo","SOUR","user1","2024-01-19"
"Levitating","Dua Lipa","Future Nostalgia","user1","2024-01-20"
"Peaches","Justin Bieber","Justice","user1","2024-01-21"
"Kiss Me More","Doja Cat","Planet Her","user1","2024-01-22"
"Montero","Lil Nas X","MONTERO","user1","2024-01-23"
"Save Your Tears","The Weeknd","After Hours","user1","2024-01-24"'''


# Convenience functions
def parse_csv(file_path: str) -> Playlist:
    """
    Parse Exportify CSV file.
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        Playlist with tracks
    """
    parser = ExportifyCSVParser()
    return parser.parse(file_path)


def parse_csv_string(content: str, playlist_name: str = "Playlist") -> Playlist:
    """
    Parse Exportify CSV from string.
    
    Args:
        content: CSV content
        playlist_name: Playlist name
        
    Returns:
        Playlist with tracks
    """
    parser = ExportifyCSVParser()
    return parser.parse_string(content, playlist_name)

