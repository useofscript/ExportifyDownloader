"""
Tests for YouTube Downloader module.
"""

import pytest
from unittest.mock import patch, MagicMock
import tempfile
import os
import subprocess
from pathlib import Path

from src.youtube_downloader import (
    YouTubeDownloader, DownloadError, get_downloader,
    _check_spotdl, _check_ytdlp,
)
from src.config import Config, reset_config


class TestYouTubeDownloader:
    """Tests for YouTubeDownloader class."""

    @pytest.fixture
    def config(self):
        """Create Config instance for tests."""
        reset_config()
        config = Config()
        config.output_dir = tempfile.mkdtemp()
        return config

    @pytest.fixture
    def downloader(self, config):
        """Create YouTubeDownloader with test config."""
        return YouTubeDownloader(config)

    def test_initialization(self, downloader):
        """Test downloader initialization."""
        assert downloader.config is not None
        assert downloader.file_manager is not None
        assert downloader.metadata_handler is not None
        assert downloader._completed_count == 0
        assert downloader._failed_count == 0
        assert downloader._skipped_count == 0
        assert downloader._consecutive_timeouts == 0
        assert downloader._backend_switched is False

    def test_get_stats(self, downloader):
        """Test stats tracking."""
        stats = downloader.get_stats()
        assert stats['completed'] == 0
        assert stats['failed'] == 0
        assert stats['skipped'] == 0

    def test_reset_stats(self, downloader):
        """Test stats reset."""
        downloader._completed_count = 5
        downloader._failed_count = 2
        downloader._skipped_count = 3
        downloader.reset_stats()
        assert downloader._completed_count == 0
        assert downloader._failed_count == 0
        assert downloader._skipped_count == 0

    def test_get_ytdl_options(self, downloader):
        """Test yt-dlp options generation (kept for API compatibility)."""
        opts = downloader._get_ytdl_options("/tmp/test", "test_file")

        assert 'bestaudio' in opts['format']
        assert opts['noplaylist'] is True
        assert opts['writethumbnail'] is True
        assert opts['continuedl'] is True
        assert opts['default_search'] == 'ytsearch'
        assert opts['max_downloads'] == 1

    def test_get_ytdl_options_output_template(self, downloader):
        """Test yt-dlp output template is set correctly."""
        opts = downloader._get_ytdl_options("/tmp/music", "My Song")
        assert "/tmp/music" in opts['outtmpl']
        assert "My Song" in opts['outtmpl']

    def test_get_ytdl_options_postprocessors(self, downloader):
        """Test yt-dlp postprocessors include audio extraction and thumbnail embedding."""
        opts = downloader._get_ytdl_options("/tmp/test", "test")
        pp_keys = [pp['key'] for pp in opts['postprocessors']]
        assert 'FFmpegExtractAudio' in pp_keys
        assert 'EmbedThumbnail' in pp_keys

    def test_setup_logger(self, downloader):
        """Test logger setup."""
        logger = downloader._setup_logger()
        assert hasattr(logger, 'debug')
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'error')

    def test_download_track_skip_existing(self, downloader, config):
        """Test that existing tracks are skipped when skip_existing is True."""
        config.skip_existing = True

        with patch.object(downloader.file_manager, 'check_track_exists', return_value=True):
            result = downloader.download_track("Test Artist", "Test Album", "Test Song")

        assert result['success'] is True
        assert result['skipped'] is True

    def test_download_track_spotdl_success(self, downloader, config):
        """Test successful download via spotdl backend."""
        config.skip_existing = False
        downloader._use_spotdl = True

        with patch.object(downloader.file_manager, 'get_track_path',
                          return_value=(Path("/tmp/test/artist/Test Song.m4a"), False)):
            with patch.object(downloader, '_download_with_spotdl',
                              return_value=(True, "/tmp/test/artist/Test Song.m4a", None)):
                result = downloader.download_track("Test Artist", "Test Album", "Test Song")

        assert result['success'] is True
        assert result['file_path'] == "/tmp/test/artist/Test Song.m4a"

    def test_download_track_spotdl_failure(self, downloader, config):
        """Test failed download via spotdl — falls back to yt-dlp."""
        config.skip_existing = False
        downloader._use_spotdl = True
        downloader._has_ytdlp = True

        with patch.object(downloader.file_manager, 'get_track_path',
                          return_value=(Path("/tmp/test/Test Song.m4a"), False)):
            with patch.object(downloader, '_download_with_spotdl',
                              return_value=(False, None, "No results found")):
                with patch.object(downloader, '_download_with_ytdlp',
                                  return_value=(True, "/tmp/test/Test Song.m4a", None)):
                    result = downloader.download_track("Test Artist", "Test Album", "Test Song")

        # Failover succeeded via yt-dlp
        assert result['success'] is True
        assert result['file_path'] == "/tmp/test/Test Song.m4a"

    def test_download_track_spotdl_failure_no_ytdlp(self, downloader, config):
        """Test failed download via spotdl when yt-dlp is unavailable."""
        config.skip_existing = False
        downloader._use_spotdl = True
        downloader._has_ytdlp = False

        with patch.object(downloader.file_manager, 'get_track_path',
                          return_value=(Path("/tmp/test/Test Song.m4a"), False)):
            with patch.object(downloader, '_download_with_spotdl',
                              return_value=(False, None, "No results found")):
                result = downloader.download_track("Test Artist", "Test Album", "Test Song")

        assert result['success'] is False
        assert result['error'] == "No results found"

    def test_download_track_ytdlp_fallback(self, downloader, config):
        """Test yt-dlp fallback when spotdl is unavailable."""
        config.skip_existing = False
        downloader._use_spotdl = False
        downloader._has_ytdlp = True

        with patch.object(downloader.file_manager, 'get_track_path',
                          return_value=(Path("/tmp/test/Test Song.m4a"), False)):
            with patch.object(downloader, '_download_with_ytdlp',
                              return_value=(True, "/tmp/test/Test Song.m4a", None)):
                result = downloader.download_track("Test Artist", "Test Album", "Test Song")

        assert result['success'] is True

    def test_download_track_rate_limited_switches_backend(self, downloader, config):
        """Test that rate-limited spotdl automatically switches to yt-dlp."""
        config.skip_existing = False
        downloader._use_spotdl = True
        downloader._has_ytdlp = True
        downloader._rate_limited.set()  # Simulate spotdl rate-limited

        with patch.object(downloader.file_manager, 'get_track_path',
                          return_value=(Path("/tmp/test/Test Song.m4a"), False)):
            with patch.object(downloader, '_download_with_ytdlp',
                              return_value=(True, "/tmp/test/Test Song.m4a", None)) as mock_ytdlp:
                result = downloader.download_track("Test Artist", "Test Album", "Test Song")

        # Should have skipped spotdl and gone straight to yt-dlp
        mock_ytdlp.assert_called_once()
        assert result['success'] is True

    def test_download_track_both_backends_unavailable(self, downloader, config):
        """Test when both backends fail."""
        config.skip_existing = False
        downloader._use_spotdl = True
        downloader._has_ytdlp = True

        with patch.object(downloader.file_manager, 'get_track_path',
                          return_value=(Path("/tmp/test/Test Song.m4a"), False)):
            with patch.object(downloader, '_download_with_spotdl',
                              return_value=(False, None, "spotdl failed")):
                with patch.object(downloader, '_download_with_ytdlp',
                                  return_value=(False, None, "yt-dlp failed")):
                    result = downloader.download_track("Test Artist", "Test Album", "Test Song")

        assert result['success'] is False
        assert result['error'] == "yt-dlp failed"

    def test_extract_lyrics_from_description(self, downloader):
        """Test lyrics extraction from video description."""
        info = {
            'description': 'Some text\nLyrics:\nLine one\nLine two\nLine three\n\nMore text'
        }
        lyrics = downloader._extract_lyrics(info)
        assert lyrics is not None
        assert 'Line one' in lyrics

    def test_extract_lyrics_no_lyrics(self, downloader):
        """Test lyrics extraction returns None when no lyrics found."""
        info = {'description': 'Just a regular description with no lyrics'}
        lyrics = downloader._extract_lyrics(info)
        assert lyrics is None

    def test_extract_lyrics_empty_description(self, downloader):
        """Test lyrics extraction with empty description."""
        info = {'description': ''}
        lyrics = downloader._extract_lyrics(info)
        assert lyrics is None

    def test_extract_lyrics_from_subtitles(self, downloader):
        """Test lyrics extraction from subtitles field."""
        info = {
            'description': '',
            'subtitles': {
                'en': [{'ext': 'srv1', 'data': '[00:01.00]Hello\n[00:05.00]World'}]
            }
        }
        lyrics = downloader._extract_lyrics(info)
        assert lyrics is not None

    @patch('src.youtube_downloader.subprocess.run')
    def test_search_track(self, mock_run, downloader):
        """Test YouTube search via subprocess."""
        mock_run.return_value = MagicMock(
            stdout="abc123\tTest Song\tTest Artist\t200\n",
            stderr="",
            returncode=0,
        )

        results = downloader.search_track("Test Artist Test Song")
        assert len(results) == 1
        assert results[0]['title'] == 'Test Song'
        assert results[0]['artist'] == 'Test Artist'
        assert results[0]['duration'] == 200

    @patch('src.youtube_downloader.subprocess.run')
    def test_search_track_empty(self, mock_run, downloader):
        """Test search returning no results."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=1)

        results = downloader.search_track("nonexistent artist song")
        assert results == []

    def test_download_batch_empty(self, downloader):
        """Test batch download with empty list."""
        results = downloader.download_batch([])
        assert results == []

    def test_download_track_exception(self, downloader, config):
        """Test download_track handles unexpected exceptions."""
        config.skip_existing = False

        with patch.object(downloader.file_manager, 'get_track_path',
                          side_effect=RuntimeError("disk error")):
            result = downloader.download_track("Artist", "Album", "Title")

        assert result['success'] is False
        assert 'disk error' in result['error']


class TestBackendDetection:
    """Tests for backend availability checks."""

    @patch('src.youtube_downloader.shutil.which', return_value='/usr/bin/spotdl')
    def test_check_spotdl_available(self, mock_which):
        assert _check_spotdl() is True

    @patch('src.youtube_downloader.shutil.which', return_value=None)
    def test_check_spotdl_unavailable(self, mock_which):
        assert _check_spotdl() is False

    @patch('src.youtube_downloader.shutil.which', return_value='/usr/bin/yt-dlp')
    def test_check_ytdlp_available(self, mock_which):
        assert _check_ytdlp() is True

    @patch('src.youtube_downloader.shutil.which', return_value=None)
    def test_check_ytdlp_unavailable(self, mock_which):
        assert _check_ytdlp() is False


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_downloader(self):
        """Test get_downloader convenience function."""
        reset_config()
        dl = get_downloader()
        assert isinstance(dl, YouTubeDownloader)

    def test_get_downloader_with_config(self):
        """Test get_downloader with explicit config."""
        config = Config()
        dl = get_downloader(config)
        assert dl.config is config
