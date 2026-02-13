"""
Tests for Config module.
"""

import pytest
import tempfile
import os
from pathlib import Path

from src.config import Config, get_config, reset_config


class TestConfig:
    """Tests for Config class."""
    
    @pytest.fixture
    def config(self):
        """Create Config instance."""
        reset_config()
        return Config()
    
    def test_default_values(self, config):
        """Test default configuration values."""
        assert config.output_dir == Path(os.path.expanduser("~/Music"))
        assert config.parallel_downloads == 4
        assert config.skip_existing is True
        assert config.create_lrc is True
        assert config.album_art_size == 1200
        assert config.audio_format == "best"
        assert config.verbose is False
    
    def test_set_output_dir(self, config):
        """Test setting output directory."""
        config.output_dir = "/custom/path"
        assert str(config.output_dir) == "/custom/path"
    
    def test_get_track_path(self, config):
        """Test track path generation."""
        path = config.get_track_path("Artist", "Album", "Title")
        
        assert "Artist" in str(path)
        assert "Album" in str(path)
        assert path.suffix == ".m4a"
    
    def test_get_track_path_custom_extension(self, config):
        """Test track path with custom extension."""
        path = config.get_track_path("Artist", "Album", "Title", ".mp3")
        assert path.suffix == ".mp3"
    
    def test_get_album_art_path(self, config):
        """Test album art path generation."""
        path = config.get_album_art_path("Artist", "Album")
        
        assert ".covers" in str(path)
        assert path.name == "album.jpg"
    
    def test_get_lrc_path(self, config):
        """Test LRC path generation."""
        path = config.get_lrc_path("Artist", "Album", "Title")
        
        assert path.name == "Title.lrc"
    
    def test_sanitize_name(self, config):
        """Test name sanitization."""
        assert config._sanitize_name("Test/Song") == "Test_Song"
        assert config._sanitize_name("Test:Song") == "Test_Song"
        assert config._sanitize_name("") == "Unknown"
        assert config._sanitize_name(None) == "Unknown"
    
    def test_sanitize_name_length_limit(self, config):
        """Test name length limit."""
        long_name = "A" * 150
        sanitized = config._sanitize_name(long_name)
        assert len(sanitized) <= 100
    
    def test_get_yt_dlp_options(self, config):
        """Test yt-dlp options generation."""
        opts = config.get_yt_dlp_options()
        
        assert isinstance(opts, dict)
        assert opts['format'] == 'best'
        assert opts['writethumbnail'] is True
        assert 'postprocessors' in opts
    
    def test_environment_variable_override(self, config):
        """Test environment variable overrides."""
        os.environ["EXPORTIFY_PARALLEL"] = "5"
        os.environ["EXPORTIFY_SKIP_EXISTING"] = "false"
        
        config = Config()  # Create new instance
        
        assert config.parallel_downloads == 5
        assert config.skip_existing is False
        
        # Cleanup
        del os.environ["EXPORTIFY_PARALLEL"]
        del os.environ["EXPORTIFY_SKIP_EXISTING"]
    
    def test_load_from_file(self):
        """Test loading configuration from file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"parallel_downloads": 5, "skip_existing": false}')
            temp_path = f.name
        
        try:
            config = Config(temp_path)
            assert config.parallel_downloads == 5
            assert config.skip_existing is False
        finally:
            os.unlink(temp_path)
    
    def test_save_config(self, config):
        """Test saving configuration."""
        config.output_dir = "/custom/path"
        config.parallel_downloads = 10
        
        with tempfile.TemporaryDirectory() as tmp:
            save_path = os.path.join(tmp, "config.json")
            config.save(save_path)
            
            # Read and verify
            import json
            with open(save_path) as f:
                saved = json.load(f)
            
            assert saved["output_dir"] == "/custom/path"
            assert saved["parallel_downloads"] == 10
    
    def test_invalid_config_file(self, tmp_path):
        """Test handling invalid config file."""
        invalid_path = tmp_path / "invalid.json"
        invalid_path.write_text("{invalid json}")
        
        # Should not raise, just warn
        config = Config(str(invalid_path))
        assert config.parallel_downloads == 4  # Default value


class TestGlobalConfig:
    """Tests for global config management."""
    
    def test_get_config_singleton(self):
        """Test that get_config returns singleton."""
        reset_config()
        
        config1 = get_config()
        config2 = get_config()
        
        assert config1 is config2
    
    def test_reset_config(self):
        """Test config reset."""
        config1 = get_config()
        config1.parallel_downloads = 99
        
        reset_config()
        config2 = get_config()
        
        assert config2.parallel_downloads == 4  # Default value

