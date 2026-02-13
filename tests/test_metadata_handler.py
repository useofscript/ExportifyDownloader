"""
Tests for Metadata Handler module.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.metadata_handler import MetadataHandler, get_metadata_handler


class TestMetadataHandler:
    """Tests for MetadataHandler class."""

    @pytest.fixture
    def handler(self):
        """Create MetadataHandler instance."""
        return MetadataHandler(max_image_size=1200)

    def test_initialization(self, handler):
        """Test handler initialization."""
        assert handler.max_image_size == 1200

    def test_initialization_custom_size(self):
        """Test handler with custom image size."""
        handler = MetadataHandler(max_image_size=800)
        assert handler.max_image_size == 800

    def test_supported_formats(self, handler):
        """Test supported format list."""
        assert '.m4a' in handler.SUPPORTED_FORMATS
        assert '.mp3' in handler.SUPPORTED_FORMATS
        assert '.flac' in handler.SUPPORTED_FORMATS
        assert '.ogg' in handler.SUPPORTED_FORMATS
        assert '.wav' in handler.SUPPORTED_FORMATS

    def test_process_metadata_file_not_found(self, handler):
        """Test metadata processing with missing file."""
        result = handler.process_metadata(
            Path("/nonexistent/file.m4a"),
            {'title': 'Test'}
        )
        assert result is False

    def test_process_metadata_unsupported_format(self, handler, tmp_path):
        """Test metadata processing with unsupported format."""
        unsupported = tmp_path / "test.xyz"
        unsupported.write_bytes(b"fake data")
        
        result = handler.process_metadata(unsupported, {'title': 'Test'})
        assert result is False

    def test_create_lrc_file(self, handler, tmp_path):
        """Test LRC file creation."""
        output = tmp_path / "test.lrc"
        lyrics = "Line one\nLine two\nLine three"
        
        result = handler.create_lrc_file(lyrics, output, artist="Test Artist", title="Test Song")
        
        assert result == output
        assert output.exists()
        
        content = output.read_text()
        assert "[ti:Test Song]" in content
        assert "[ar:Test Artist]" in content
        assert "Line one" in content
        assert "Line two" in content

    def test_create_lrc_file_with_timestamps(self, handler, tmp_path):
        """Test LRC file creation with pre-existing timestamps."""
        output = tmp_path / "test.lrc"
        lyrics = "[00:05.00]Line one\n[00:10.00]Line two"
        
        handler.create_lrc_file(lyrics, output, artist="Artist", title="Song")
        
        content = output.read_text()
        # Should preserve existing timestamps, not add [00:00.00]
        assert "[00:05.00]Line one" in content
        assert "[00:10.00]Line two" in content

    def test_create_lrc_file_creates_directory(self, handler, tmp_path):
        """Test LRC file creation creates parent directories."""
        output = tmp_path / "sub" / "dir" / "test.lrc"
        
        handler.create_lrc_file("Lyrics", output, "Artist", "Song")
        
        assert output.exists()

    def test_has_timestamp_true(self, handler):
        """Test timestamp detection - positive."""
        assert handler._has_timestamp("[00:05.00]Hello") is True
        assert handler._has_timestamp("[01:30.50]World") is True

    def test_has_timestamp_false(self, handler):
        """Test timestamp detection - negative."""
        assert handler._has_timestamp("No timestamp here") is False
        assert handler._has_timestamp("[ti:Title]") is False

    def test_parse_lrc_file(self, handler, tmp_path):
        """Test LRC file parsing."""
        lrc_file = tmp_path / "test.lrc"
        lrc_file.write_text("[00:05.00]Line one\n[00:10.50]Line two\n")
        
        result = handler.parse_lrc_file(lrc_file)
        
        assert isinstance(result, dict)
        assert len(result) == 2

    def test_parse_lrc_file_not_found(self, handler, tmp_path):
        """Test LRC parsing with missing file."""
        result = handler.parse_lrc_file(tmp_path / "missing.lrc")
        assert result == {}

    def test_process_album_art(self, handler, tmp_path):
        """Test album art processing with a real image."""
        from PIL import Image
        
        # Create a test image (2000x2000 - larger than max)
        img = Image.new('RGB', (2000, 2000), color='red')
        source = tmp_path / "source.jpg"
        img.save(source)
        
        output = tmp_path / "output.jpg"
        result = handler.process_album_art(source, output)
        
        assert result is not None
        assert result.exists()
        
        # Verify it was resized
        with Image.open(result) as resized:
            assert resized.width <= 1200
            assert resized.height <= 1200

    def test_process_album_art_small_image(self, handler, tmp_path):
        """Test album art processing with image already smaller than max."""
        from PIL import Image
        
        img = Image.new('RGB', (800, 600), color='blue')
        source = tmp_path / "small.jpg"
        img.save(source)
        
        output = tmp_path / "output.jpg"
        result = handler.process_album_art(source, output)
        
        assert result is not None
        with Image.open(result) as resized:
            assert resized.width <= 800
            assert resized.height <= 600

    def test_process_album_art_rgba(self, handler, tmp_path):
        """Test album art processing with RGBA image."""
        from PIL import Image
        
        img = Image.new('RGBA', (500, 500), color=(255, 0, 0, 128))
        source = tmp_path / "rgba.png"
        img.save(source)
        
        output = tmp_path / "output.jpg"
        result = handler.process_album_art(source, output)
        
        assert result is not None
        with Image.open(result) as converted:
            assert converted.mode == 'RGB'

    def test_process_album_art_missing_file(self, handler, tmp_path):
        """Test album art processing with missing source."""
        result = handler.process_album_art(tmp_path / "missing.jpg")
        assert result is None

    def test_read_metadata_missing_file(self, handler, tmp_path):
        """Test reading metadata from missing file."""
        result = handler.read_metadata(tmp_path / "missing.m4a")
        assert result == {}


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_metadata_handler(self):
        """Test get_metadata_handler function."""
        handler = get_metadata_handler()
        assert isinstance(handler, MetadataHandler)
        assert handler.max_image_size == 1200

    def test_get_metadata_handler_custom_size(self):
        """Test get_metadata_handler with custom size."""
        handler = get_metadata_handler(800)
        assert handler.max_image_size == 800
