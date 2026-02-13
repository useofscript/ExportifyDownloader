"""
Tests for CSV Parser module.
"""

import pytest
import tempfile
import os
from pathlib import Path

from src.csv_parser import (
    ExportifyCSVParser,
    parse_csv,
    parse_csv_string,
    Track,
    Playlist,
    CSVParseError,
)


class TestTrack:
    """Tests for Track dataclass."""
    
    def test_track_creation(self):
        """Test basic track creation."""
        track = Track(
            track_name="Test Song",
            artist_name="Test Artist",
            album_name="Test Album"
        )
        
        assert track.track_name == "Test Song"
        assert track.artist_name == "Test Artist"
        assert track.album_name == "Test Album"
        assert track.added_by == ""
        assert track.added_at == ""
    
    def test_track_with_optional_fields(self):
        """Test track with optional fields."""
        track = Track(
            track_name="Test Song",
            artist_name="Test Artist",
            album_name="Test Album",
            added_by="user1",
            added_at="2024-01-15",
            track_number="1"
        )
        
        assert track.added_by == "user1"
        assert track.added_at == "2024-01-15"
        assert track.track_number == "1"
    
    def test_get_search_query(self):
        """Test search query generation."""
        track = Track(
            track_name="Blinding Lights",
            artist_name="The Weeknd",
            album_name="After Hours"
        )
        
        query = track.get_search_query()
        assert query == "The Weeknd - Blinding Lights"
    
    def test_get_download_filename(self):
        """Test download filename generation."""
        track = Track(
            track_name="Test/Song?",
            artist_name="Test Artist",
            album_name="Test Album"
        )
        
        filename = track.get_download_filename()
        assert "/" not in filename
        assert "?" not in filename
    
    def test_to_dict(self):
        """Test track to dictionary conversion."""
        track = Track(
            track_name="Test Song",
            artist_name="Test Artist",
            album_name="Test Album",
            added_by="user1"
        )
        
        result = track.to_dict()
        assert isinstance(result, dict)
        assert result["track_name"] == "Test Song"
        assert result["artist_name"] == "Test Artist"


class TestPlaylist:
    """Tests for Playlist dataclass."""
    
    def test_empty_playlist(self):
        """Test empty playlist."""
        playlist = Playlist(name="Test Playlist")
        
        assert len(playlist) == 0
        assert playlist.get_artists() == []
        assert playlist.get_albums() == []
    
    def test_playlist_with_tracks(self):
        """Test playlist with tracks."""
        tracks = [
            Track(track_name="Song 1", artist_name="Artist A", album_name="Album 1"),
            Track(track_name="Song 2", artist_name="Artist A", album_name="Album 1"),
            Track(track_name="Song 3", artist_name="Artist B", album_name="Album 2"),
        ]
        
        playlist = Playlist(name="Test Playlist", tracks=tracks)
        
        assert len(playlist) == 3
        assert len(playlist.get_artists()) == 2
        assert len(playlist.get_albums()) == 2
    
    def test_get_stats(self):
        """Test playlist statistics."""
        tracks = [
            Track(track_name="Song 1", artist_name="Artist A", album_name="Album 1"),
            Track(track_name="Song 2", artist_name="Artist A", album_name="Album 1"),
            Track(track_name="Song 3", artist_name="Artist B", album_name="Album 2"),
        ]
        
        playlist = Playlist(name="Test Playlist", tracks=tracks)
        stats = playlist.get_stats()
        
        assert stats["total_tracks"] == 3
        assert stats["unique_artists"] == 2
        assert stats["unique_albums"] == 2


class TestExportifyCSVParser:
    """Tests for ExportifyCSVParser class."""
    
    def test_parse_valid_csv(self):
        """Test parsing valid CSV."""
        csv_content = '''Track Name,Artist Name,Album Name,Added By,Added At
"Song 1","Artist A","Album 1","user1","2024-01-01"
"Song 2","Artist B","Album 2","user1","2024-01-02"'''
        
        parser = ExportifyCSVParser()
        playlist = parser.parse_string(csv_content)
        
        assert len(playlist) == 2
        assert playlist.tracks[0].track_name == "Song 1"
        assert playlist.tracks[0].artist_name == "Artist A"
    
    def test_parse_csv_with_quotes(self):
        """Test parsing CSV with quoted fields."""
        csv_content = '''Track Name,Artist Name,Album Name
"Song, With, Commas","Artist, Name","Album, Name"'''
        
        parser = ExportifyCSVParser()
        playlist = parser.parse_string(csv_content)
        
        assert len(playlist) == 1
        assert playlist.tracks[0].track_name == "Song, With, Commas"
    
    def test_parse_empty_file(self):
        """Test parsing empty file raises error."""
        parser = ExportifyCSVParser()
        
        with pytest.raises(CSVParseError):
            parser.parse_string("")
    
    def test_parse_missing_columns(self):
        """Test parsing file with missing columns."""
        csv_content = '''Track Name,Artist Name
"Song 1","Artist A"'''
        
        parser = ExportifyCSVParser()
        
        with pytest.raises(CSVParseError):
            parser.parse_string(csv_content)
    
    def test_parse_skip_empty_rows(self):
        """Test that empty rows are skipped."""
        csv_content = '''Track Name,Artist Name,Album Name
"Song 1","Artist A","Album 1"

"Song 2","Artist B","Album 2"'''
        
        parser = ExportifyCSVParser()
        playlist = parser.parse_string(csv_content)
        
        assert len(playlist) == 2
    
    def test_parse_file(self):
        """Test parsing actual file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write('''Track Name,Artist Name,Album Name,Added By,Added At
"Song 1","Artist A","Album 1","user1","2024-01-01"
"Song 2","Artist B","Album 2","user1","2024-01-02"''')
            temp_path = f.name
        
        try:
            parser = ExportifyCSVParser()
            playlist = parser.parse(temp_path)
            
            assert len(playlist) == 2
            assert playlist.source_file == os.path.abspath(temp_path)
        finally:
            os.unlink(temp_path)
    
    def test_get_sample_csv(self):
        """Test sample CSV generation."""
        parser = ExportifyCSVParser()
        sample = parser.get_sample_csv()
        
        assert "Track Name" in sample
        assert "Artist Name" in sample
        assert "Shape of You" in sample
    
    def test_parse_file_not_found(self):
        """Test parsing non-existent file."""
        parser = ExportifyCSVParser()
        
        with pytest.raises(FileNotFoundError):
            parser.parse("/nonexistent/file.csv")
    
    def test_column_normalization(self):
        """Test column name normalization."""
        csv_content = '''track name,artist name,album name,added by,added at
"Song 1","Artist A","Album 1","user1","2024-01-01"'''
        
        parser = ExportifyCSVParser()
        playlist = parser.parse_string(csv_content)
        
        assert len(playlist) == 1


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_parse_csv_function(self):
        """Test parse_csv convenience function."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write('''Track Name,Artist Name,Album Name
"Song 1","Artist A","Album 1"''')
            temp_path = f.name
        
        try:
            playlist = parse_csv(temp_path)
            assert len(playlist) == 1
        finally:
            os.unlink(temp_path)
    
    def test_parse_csv_string_function(self):
        """Test parse_csv_string convenience function."""
        csv_content = '''Track Name,Artist Name,Album Name
"Song 1","Artist A","Album 1"'''
        
        playlist = parse_csv_string(csv_content, "Test Playlist")
        assert len(playlist) == 1
        assert playlist.name == "Test Playlist"

