"""
Tests for File Manager module.
"""

import pytest
import tempfile
import os
from pathlib import Path

from src.file_manager import FileManager, get_file_manager


class TestFileManager:
    """Tests for FileManager class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmp:
            yield Path(tmp)
    
    @pytest.fixture
    def file_manager(self, temp_dir):
        """Create FileManager instance with temp directory."""
        return FileManager(str(temp_dir))
    
    def test_initialization(self, temp_dir):
        """Test FileManager initialization."""
        fm = FileManager(str(temp_dir))
        assert fm.base_dir == temp_dir
    
    def test_get_album_folder(self, file_manager, temp_dir):
        """Test album folder creation."""
        folder = file_manager.get_album_folder("Test Artist", "Test Album")
        
        expected = temp_dir / "Test Artist" / "Test Album"
        assert folder == expected
        assert folder.exists()
    
    def test_get_track_path_new(self, file_manager):
        """Test getting path for new track."""
        path, exists = file_manager.get_track_path(
            "Test Artist", "Test Album", "Test Song"
        )
        
        assert path.name == "Test Artist - Test Song.m4a"
        assert not exists
    
    def test_get_track_path_existing(self, file_manager, temp_dir):
        """Test getting path for existing track."""
        # Create file first
        folder = temp_dir / "Test Artist" / "Test Album"
        folder.mkdir(parents=True)
        existing_file = folder / "Test Artist - Test Song.m4a"
        existing_file.touch()
        
        path, exists = file_manager.get_track_path(
            "Test Artist", "Test Album", "Test Song"
        )
        
        # Should return different path due to conflict handling
        assert exists
    
    def test_check_track_exists_false(self, file_manager):
        """Test checking non-existent track."""
        exists = file_manager.check_track_exists(
            "Test Artist", "Test Album", "Nonexistent Song"
        )
        assert not exists
    
    def test_check_track_exists_true(self, file_manager, temp_dir):
        """Test checking existing track."""
        # Create file
        folder = temp_dir / "Test Artist" / "Test Album"
        folder.mkdir(parents=True)
        existing_file = folder / "Test Artist - Test Song.m4a"
        existing_file.touch()
        
        exists = file_manager.check_track_exists(
            "Test Artist", "Test Album", "Test Song"
        )
        assert exists
    
    def test_get_album_art_path_album(self, file_manager, temp_dir):
        """Test getting album art path."""
        art_path = file_manager.get_album_art_path(
            "Test Artist", "Test Album"
        )
        
        expected = temp_dir / "Test Artist" / "Test Album" / ".covers" / "album.jpg"
        assert art_path == expected
        assert art_path.parent.exists()
    
    def test_get_album_art_path_track(self, file_manager, temp_dir):
        """Test getting track-specific art path."""
        art_path = file_manager.get_album_art_path(
            "Test Artist", "Test Album",
            is_track_specific=True,
            track_title="Test Song"
        )
        
        expected = temp_dir / "Test Artist" / "Test Album" / ".Test Song.cover.jpg"
        assert art_path == expected
    
    def test_get_lrc_path(self, file_manager, temp_dir):
        """Test getting LRC file path."""
        lrc_path = file_manager.get_lrc_path(
            "Test Artist", "Test Album", "Test Song"
        )
        
        expected = temp_dir / "Test Artist" / "Test Album" / "Test Song.lrc"
        assert lrc_path == expected
    
    def test_sanitize_filename_special_chars(self):
        """Test filename sanitization with special characters."""
        # Create fresh instance for each test
        fm = FileManager("~/Music")
        
        assert fm._sanitize_filename("Test/Song") == "Test and Song"
        assert fm._sanitize_filename("Test:Song") == "Test - Song"
        assert fm._sanitize_filename('Test"Song') == "Test'Song"
    
    def test_sanitize_filename_length(self):
        """Test filename length limit."""
        fm = FileManager("~/Music")
        
        long_name = "A" * 100
        sanitized = fm._sanitize_filename(long_name)
        assert len(sanitized) <= 80
    
    def test_sanitize_folder_name(self):
        """Test folder name sanitization."""
        fm = FileManager("~/Music")
        
        assert fm._sanitize_folder_name("Test/Folder") == "TestFolder"
        assert fm._sanitize_folder_name("") == "Unknown"
    
    def test_save_lrc_file(self, file_manager):
        """Test saving LRC file."""
        lyrics = """[00:00.00]Line 1
[00:05.00]Line 2"""
        
        lrc_path = file_manager.save_lrc_file(
            "Test Artist", "Test Album", "Test Song", lyrics
        )
        
        assert lrc_path.exists()
        with open(lrc_path) as f:
            content = f.read()
        assert "Line 1" in content
    
    def test_list_tracks(self, file_manager, temp_dir):
        """Test listing tracks."""
        # Create test files
        folder = temp_dir / "Test Artist" / "Test Album"
        folder.mkdir(parents=True)
        
        (folder / "Test Artist - Song 1.m4a").touch()
        (folder / "Test Artist - Song 2.m4a").touch()
        
        tracks = file_manager.list_tracks("Test Artist", "Test Album")
        
        assert len(tracks) == 2
    
    def test_get_folder_size(self, file_manager, temp_dir):
        """Test getting folder size."""
        # Create test files with content
        folder = temp_dir / "Test Artist" / "Test Album"
        folder.mkdir(parents=True)
        
        test_file = folder / "Test Song.m4a"
        test_file.write_bytes(b"x" * 1000)
        
        size = file_manager.get_folder_size()
        
        assert size >= 1000
    
    def test_format_size(self):
        """Test size formatting."""
        fm = FileManager("~/Music")
        
        assert fm.format_size(500) == "500.00 B"
        assert fm.format_size(1500) == "1.46 KB"
        assert fm.format_size(1500000) == "1.43 MB"
    
    def test_cleanup_empty_folders(self, file_manager, temp_dir):
        """Test cleanup of empty folders."""
        # Create empty folders
        folder = temp_dir / "Empty Artist" / "Empty Album"
        folder.mkdir(parents=True)
        
        # Create another empty folder
        folder2 = temp_dir / "Another Artist"
        folder2.mkdir()
        
        removed = file_manager.cleanup_empty_folders()
        
        assert removed >= 2
        assert not (temp_dir / "Empty Artist").exists()
    
    def test_handle_filename_conflict(self, file_manager, temp_dir):
        """Test filename conflict resolution."""
        # Create existing file
        folder = temp_dir / "Test"
        folder.mkdir()
        existing = folder / "Test Song.m4a"
        existing.touch()
        
        new_path = file_manager._handle_filename_conflict(existing)
        
        # Should be different path
        assert new_path.name == "Test Song (1).m4a"
    
    def test_move_file(self, file_manager, temp_dir):
        """Test moving files."""
        # Create source file
        source = temp_dir / "source.m4a"
        source.write_bytes(b"test data")
        
        # Move to destination
        dest = temp_dir / "dest" / "file.m4a"
        new_path = file_manager.move_file(source, dest)
        
        assert new_path.exists()
        assert not source.exists()
    
    def test_copy_file(self, file_manager, temp_dir):
        """Test copying files."""
        # Create source file
        source = temp_dir / "source.m4a"
        source.write_bytes(b"test data")
        
        # Copy to destination
        dest = temp_dir / "dest" / "file.m4a"
        new_path = file_manager.copy_file(source, dest)
        
        assert new_path.exists()
        assert source.exists()


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_get_file_manager(self):
        """Test get_file_manager function."""
        fm = get_file_manager("/tmp/test")
        assert isinstance(fm, FileManager)
        assert fm.base_dir == Path("/tmp/test")

