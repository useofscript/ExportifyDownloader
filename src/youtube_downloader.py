"""
YouTube Downloader for music tracks.
Uses spotdl (with yt-dlp backend) for searching, downloading, and tagging.
Falls back to raw yt-dlp if spotdl is unavailable.
"""

import os
import subprocess
import shutil
import json
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from rich.progress import Progress, SpinnerColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn, TimeRemainingColumn, TextColumn
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from src.config import Config, get_config
from src.file_manager import FileManager
from src.metadata_handler import MetadataHandler


console = Console()


class DownloadError(Exception):
    """Custom exception for download errors."""
    pass


def _check_spotdl() -> bool:
    """Check if spotdl is available."""
    return shutil.which('spotdl') is not None


def _check_ytdlp() -> bool:
    """Check if yt-dlp is available."""
    return shutil.which('yt-dlp') is not None


class YouTubeDownloader:
    """
    Downloads music from YouTube using spotdl (preferred) or yt-dlp.

    Features:
    - Best quality audio detection
    - Progress tracking
    - Resume capability
    - Batch processing
    - Album art extraction & embedding
    - Lyrics / LRC generation
    - Automatic metadata tagging
    """

    def __init__(self, config: Config = None):
        """
        Initialize YouTube downloader.

        Args:
            config: Configuration object
        """
        self.config = config or get_config()
        self.file_manager = FileManager(str(self.config.output_dir))
        self.metadata_handler = MetadataHandler(self.config.album_art_size)

        # Track download state
        self._download_lock = threading.Lock()
        self._completed_count = 0
        self._failed_count = 0
        self._skipped_count = 0

        # Cancellation & rate-limit detection
        self._cancelled = threading.Event()
        self._rate_limited = threading.Event()
        self._consecutive_timeouts = 0

        # Console for output
        self.console = Console()

        # Detect available backends
        self._use_spotdl = _check_spotdl()
        self._has_ytdlp = _check_ytdlp()
        self._backend_switched = False  # True once we auto-switched from spotdl→yt-dlp

    # ------------------------------------------------------------------ #
    #  Single track download
    # ------------------------------------------------------------------ #

    def download_track(self, artist: str, album: str, title: str,
                       search_query: str = None,
                       progress_callback: Callable = None) -> Dict[str, Any]:
        """
        Download a single track from YouTube.

        Args:
            artist: Artist name
            album: Album name
            title: Track title
            search_query: Optional custom search query
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary with download result
        """
        result: Dict[str, Any] = {
            'artist': artist,
            'album': album,
            'title': title,
            'success': False,
            'file_path': None,
            'error': None,
        }

        try:
            # Bail early if cancelled
            if self._cancelled.is_set():
                result['error'] = 'Cancelled'
                return result

            # Check if already exists
            if self.config.skip_existing:
                if self.file_manager.check_track_exists(artist, album, title):
                    result['success'] = True
                    result['skipped'] = True
                    result['message'] = 'Already exists, skipping'
                    with self._download_lock:
                        self._skipped_count += 1
                    return result

            # Build the output path the file should end up at
            track_path, _ = self.file_manager.get_track_path(artist, album, title)
            output_dir = str(track_path.parent)

            ok, fpath, err = False, None, None

            # Try primary backend
            use_spotdl = self._use_spotdl and not self._rate_limited.is_set()
            if use_spotdl:
                ok, fpath, err = self._download_with_spotdl(
                    artist, album, title, output_dir, search_query)

            # Failsafe: if primary backend failed/timed-out/rate-limited,
            # automatically switch to the other backend for this track.
            if not ok and self._has_ytdlp:
                if use_spotdl and not self._backend_switched and self._rate_limited.is_set():
                    self._backend_switched = True
                    self.console.print(
                        "\n[yellow bold]⚡ Switching to yt-dlp backend "
                        "(spotdl rate-limited)[/yellow bold]")
                ok, fpath, err = self._download_with_ytdlp(
                    artist, album, title, output_dir, search_query)

            # If spotdl was skipped (rate-limited) and yt-dlp not available
            if not ok and not use_spotdl and not self._has_ytdlp:
                err = 'All download backends unavailable'

            if ok and fpath:
                result['success'] = True
                result['file_path'] = fpath
                with self._download_lock:
                    self._completed_count += 1
            else:
                result['error'] = err or 'Could not find video'
                with self._download_lock:
                    self._failed_count += 1

        except Exception as e:
            result['error'] = str(e)
            with self._download_lock:
                self._failed_count += 1

        return result

    # ------------------------------------------------------------------ #
    #  Batch download
    # ------------------------------------------------------------------ #

    def _build_live_display(self, total: int, done: int,
                            active_tracks: List[str],
                            last_results: List[Dict[str, Any]]) -> Panel:
        """Build a rich renderable for the Live display."""
        # --- progress bar ---
        pct = done / total if total else 0
        bar_width = 40
        filled = int(bar_width * pct)
        bar = f"[green]{'━' * filled}[/green][dim]{'━' * (bar_width - filled)}[/dim]"
        progress_line = f"  {bar}  [bold]{done}[/bold]/{total}  ({pct:.0%})"

        # --- stats ---
        ok = self._completed_count
        fail = self._failed_count
        skip = self._skipped_count
        stats_line = (f"  [green]✓ {ok}[/green]  "
                      f"[red]✗ {fail}[/red]  "
                      f"[yellow]⊘ {skip} skipped[/yellow]")

        # --- currently downloading ---
        active_section = ""
        if active_tracks:
            active_section = "\n  [bold cyan]Downloading:[/bold cyan]"
            for name in active_tracks:
                active_section += f"\n    [cyan]♫[/cyan] {name}"

        # --- recent results (last 3) ---
        recent_section = ""
        if last_results:
            recent_section = "\n  [dim]Recent:[/dim]"
            for r in last_results[-3:]:
                label = f"{r.get('artist', '?')} – {r.get('title', '?')}"
                if r.get('skipped'):
                    recent_section += f"\n    [yellow]⊘[/yellow] [dim]{label}[/dim]"
                elif r.get('success'):
                    recent_section += f"\n    [green]✓[/green] {label}"
                else:
                    err = (r.get('error') or 'error')[:50]
                    recent_section += f"\n    [red]✗[/red] {label} [dim red]({err})[/dim red]"

        body = f"{progress_line}\n{stats_line}{active_section}{recent_section}"
        return Panel(body, title="[bold]Exportify Downloader[/bold]", border_style="blue")

    def download_batch(self, tracks: List[Dict[str, str]],
                       progress_callback: Callable = None) -> List[Dict[str, Any]]:
        """
        Download multiple tracks with a live in-place progress display.

        Handles Ctrl+C gracefully and aborts early on rate limits.

        Args:
            tracks: List of dicts with 'artist', 'album', 'title'
            progress_callback: Optional callback(completed, total)

        Returns:
            List of download results
        """
        results: List[Dict[str, Any]] = []
        total = len(tracks)
        if total == 0:
            return results

        # Reset cancellation flags
        self._cancelled.clear()
        self._rate_limited.clear()

        active_tracks: List[str] = []
        active_lock = threading.Lock()

        def _wrapped_download(track: Dict[str, str]) -> Dict[str, Any]:
            # Skip work only if user cancelled (Ctrl+C)
            if self._cancelled.is_set():
                return {
                    'artist': track['artist'],
                    'album': track['album'],
                    'title': track['title'],
                    'success': False,
                    'error': 'Cancelled',
                }

            label = f"{track['artist']} – {track['title']}"
            with active_lock:
                active_tracks.append(label)
            try:
                return self.download_track(
                    artist=track['artist'],
                    album=track['album'],
                    title=track['title'],
                    search_query=track.get('search_query'),
                )
            finally:
                with active_lock:
                    if label in active_tracks:
                        active_tracks.remove(label)

        try:
            with Live(
                self._build_live_display(total, 0, [], []),
                console=self.console,
                refresh_per_second=4,
                transient=True,
            ) as live:
                with ThreadPoolExecutor(
                    max_workers=self.config.parallel_downloads
                ) as executor:
                    futures = {}
                    for track in tracks:
                        future = executor.submit(_wrapped_download, track)
                        futures[future] = track

                    for future in as_completed(futures):
                        track = futures[future]
                        try:
                            result = future.result()
                            results.append(result)
                        except Exception as e:
                            results.append({
                                'artist': track['artist'],
                                'album': track['album'],
                                'title': track['title'],
                                'success': False,
                                'error': str(e),
                            })

                        with active_lock:
                            snapshot = list(active_tracks)
                        live.update(
                            self._build_live_display(
                                total, len(results), snapshot, results))

                        if progress_callback:
                            progress_callback(len(results), total)

                        # If BOTH backends are exhausted, stop
                        if (self._rate_limited.is_set()
                                and not self._has_ytdlp):
                            self._cancelled.set()
                            for f in futures:
                                f.cancel()
                            break

        except KeyboardInterrupt:
            self._cancelled.set()
            self.console.print(
                "\n[yellow]Stopping downloads... please wait for active tracks to finish.[/yellow]")
            # Cancel any pending (not yet started) futures
            for f in futures:
                f.cancel()

        if self._rate_limited.is_set() and not self._has_ytdlp:
            self.console.print(
                "\n[red bold]Rate limited and no fallback backend available.[/red bold] "
                "Try again later or install yt-dlp.")

        return results

    # ------------------------------------------------------------------ #
    #  spotdl backend
    # ------------------------------------------------------------------ #

    def _download_with_spotdl(self, artist: str, album: str, title: str,
                              output_dir: str,
                              search_query: str = None) -> tuple:
        """
        Download a track using spotdl subprocess.

        Uses a short timeout (15s) because spotdl hangs indefinitely when
        rate-limited and buffers all output until killed.  After the timeout
        kills the process, we inspect the captured output for a rate-limit
        message.

        Returns:
            (success: bool, file_path: str | None, error: str | None)
        """
        # Bail immediately if already rate-limited or cancelled
        if self._rate_limited.is_set() or self._cancelled.is_set():
            return False, None, "Cancelled"

        query = search_query or f"{artist} - {title}"

        # spotdl output template — put file in the target directory
        output_template = os.path.join(output_dir, "{artist} - {title}")

        cmd = [
            "spotdl", "download", query,
            "--output", output_template,
            "--format", "m4a",
            "--bitrate", "auto",
            "--threads", "4",
            "--print-errors",
            "--overwrite", "skip" if self.config.skip_existing else "force",
        ]

        if self.config.create_lrc:
            cmd.append("--generate-lrc")

        # 45s timeout — generous enough for real downloads on slower connections,
        # but catches rate-limit hangs. 3 consecutive timeouts = rate-limited.
        timeout = min(self.config.download_timeout, 45)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            combined = (proc.stdout or "") + (proc.stderr or "")

            if self._is_rate_limited_output(combined):
                self._rate_limited.set()
                return False, None, "Rate limited — try again later"

            # Look for the downloaded file in output_dir
            output_path = Path(output_dir)
            candidates = sorted(
                output_path.glob("*.m4a"),
                key=os.path.getmtime,
                reverse=True,
            )

            if candidates:
                # Reset consecutive failures on success
                with self._download_lock:
                    self._consecutive_timeouts = 0
                return True, str(candidates[0]), None

            # If no file found, treat as failure
            err_msg = combined.strip()[:200] or "spotdl produced no output file"
            return False, None, err_msg

        except subprocess.TimeoutExpired as e:
            # spotdl buffers output — on kill, Python captures what was buffered
            captured = ""
            if e.stdout:
                captured += e.stdout if isinstance(e.stdout, str) else e.stdout.decode("utf-8", errors="replace")
            if e.stderr:
                captured += e.stderr if isinstance(e.stderr, str) else e.stderr.decode("utf-8", errors="replace")

            if self._is_rate_limited_output(captured):
                self._rate_limited.set()
                return False, None, "Rate limited — try again later"

            # Track consecutive timeouts — 3 in a row = likely rate-limited
            with self._download_lock:
                self._consecutive_timeouts += 1
                if self._consecutive_timeouts >= 3:
                    self._rate_limited.set()
                    return False, None, "Multiple timeouts — likely rate limited"

            return False, None, "Download timed out"

        except FileNotFoundError:
            return False, None, "spotdl not found — install with: pip install spotdl"
        except Exception as e:
            return False, None, str(e)

    @staticmethod
    def _is_rate_limited_output(text: str) -> bool:
        """Check if output text indicates a rate limit."""
        lower = text.lower()
        return "rate" in lower and "limit" in lower

    # ------------------------------------------------------------------ #
    #  yt-dlp fallback backend
    # ------------------------------------------------------------------ #

    def _download_with_ytdlp(self, artist: str, album: str, title: str,
                             output_dir: str,
                             search_query: str = None) -> tuple:
        """
        Download a track using yt-dlp subprocess (fallback).

        Returns:
            (success: bool, file_path: str | None, error: str | None)
        """
        query = search_query or f"{artist} {title} {album} audio"
        filename = f"{artist} - {title}"
        output_template = os.path.join(output_dir, filename + ".%(ext)s")

        cmd = [
            "yt-dlp",
            f"ytsearch:{query}",
            "--format", "bestaudio[ext=m4a]/bestaudio/best",
            "-x", "--audio-format", "m4a",
            "--audio-quality", "0",
            "-o", output_template,
            "--max-downloads", "1",
            "--no-playlist",
            "--concurrent-fragments", "4",
            "--retries", str(self.config.max_retries),
            "--no-warnings",
        ]

        # Overwrite existing files when skip_existing is disabled
        if not self.config.skip_existing:
            cmd.append("--force-overwrites")

        # Add deno runtime if available
        if shutil.which("deno"):
            cmd.extend(["--js-runtimes", "deno"])

        # 60s is generous for a single track — avoids blocking too long on fallback
        yt_timeout = min(self.config.download_timeout, 60)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=yt_timeout,
            )

            # Look for the downloaded file
            output_path = Path(output_dir)
            candidates = sorted(
                output_path.glob(f"{filename}.*"),
                key=os.path.getmtime,
                reverse=True,
            )
            audio_candidates = [
                c for c in candidates
                if c.suffix in ('.m4a', '.mp3', '.opus', '.ogg', '.wav')
            ]

            if audio_candidates:
                return True, str(audio_candidates[0]), None

            stderr = (proc.stderr or "").strip()
            return False, None, stderr or "yt-dlp produced no output file"

        except subprocess.TimeoutExpired:
            return False, None, "Download timed out"
        except FileNotFoundError:
            return False, None, "yt-dlp not found — install with: pip install yt-dlp"
        except Exception as e:
            return False, None, str(e)

    # ------------------------------------------------------------------ #
    #  yt-dlp options (kept for API compatibility with tests)
    # ------------------------------------------------------------------ #

    def _get_ytdl_options(self, output_dir: str, filename: str) -> dict:
        """
        Get yt-dlp options for download.

        Args:
            output_dir: Output directory
            filename: Filename pattern

        Returns:
            yt-dlp options dictionary
        """
        output_template = os.path.join(output_dir, filename + '.%(ext)s')

        opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl': output_template,
            'writethumbnail': True,
            'writelinks': False,
            'writeinfojson': False,
            'writedescription': False,
            'noplaylist': True,
            'nocheckcertificate': False,
            'no_warnings': False,
            'quiet': False,
            'no_color': False,
            'verbose': self.config.verbose,
            'progress': True,
            'concurrent-fragments': 4,
            'retries': self.config.max_retries,
            'timeout': self.config.download_timeout,
            'continuedl': True,
            'extractaudio': True,
            'audiocodec': 'aac',
            'audioquality': '0',
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'm4a',
                    'preferredquality': '0',
                },
                {
                    'key': 'EmbedThumbnail',
                },
            ],
            'default_search': 'ytsearch',
            'max_downloads': 1,
            'logger': self._setup_logger(),
        }

        return opts

    # ------------------------------------------------------------------ #
    #  Lyrics extraction (used with yt-dlp path)
    # ------------------------------------------------------------------ #

    def _extract_lyrics(self, info: dict) -> Optional[str]:
        """
        Extract lyrics from video info dictionary.

        Args:
            info: Video info dictionary from yt-dlp

        Returns:
            Lyrics string or None
        """
        description = info.get('description', '')

        if description:
            lines = description.split('\n')
            lyrics_lines = []
            in_lyrics = False

            for line in lines:
                if any(m in line.lower() for m in
                       ['lyrics', 'lyric', 'letra', 'paroles']):
                    in_lyrics = True
                    continue

                if in_lyrics:
                    if line.strip():
                        lyrics_lines.append(line.strip())
                    else:
                        if lyrics_lines:
                            break

            if lyrics_lines:
                return '\n'.join(lyrics_lines)

        # Try subtitles
        subtitles = info.get('subtitles', {})
        if subtitles:
            sub_data = subtitles.get('en') or next(
                iter(subtitles.values()), None)
            if sub_data and isinstance(sub_data, list):
                for sub in sub_data:
                    if sub.get('ext') in ('srv1', 'vtt', 'srt', 'json3'):
                        if sub.get('data'):
                            return sub['data']

        return None

    # ------------------------------------------------------------------ #
    #  Logger (yt-dlp path)
    # ------------------------------------------------------------------ #

    def _setup_logger(self) -> object:
        """Setup custom logger for yt-dlp."""
        class YTDLLogger:
            def debug(self, msg):
                if self.verbose:
                    console.print(f"[dim]{msg}[/dim]")

            def info(self, msg):
                console.print(f"[cyan]{msg}[/cyan]")

            def warning(self, msg):
                console.print(f"[yellow]Warning: {msg}[/yellow]")

            def error(self, msg):
                console.print(f"[red]Error: {msg}[/red]")

        logger = YTDLLogger()
        logger.verbose = self.config.verbose
        return logger

    # ------------------------------------------------------------------ #
    #  Search
    # ------------------------------------------------------------------ #

    def search_track(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for tracks on YouTube.

        Args:
            query: Search query

        Returns:
            List of search results
        """
        try:
            cmd = [
                "yt-dlp", f"ytsearch5:{query}",
                "--flat-playlist",
                "--print", "%(id)s\t%(title)s\t%(uploader)s\t%(duration)s",
            ]
            if shutil.which("deno"):
                cmd.extend(["--js-runtimes", "deno"])

            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30)

            results = []
            for line in (proc.stdout or "").strip().split('\n'):
                if not line.strip():
                    continue
                parts = line.split('\t')
                if len(parts) >= 4:
                    results.append({
                        'title': parts[1],
                        'artist': parts[2],
                        'url': f"https://www.youtube.com/watch?v={parts[0]}",
                        'duration': (int(parts[3])
                                     if parts[3].isdigit() else 0),
                        'thumbnail': '',
                    })
            return results

        except Exception as e:
            console.print(f"[red]Search error: {e}[/red]")
            return []

    # ------------------------------------------------------------------ #
    #  Stats
    # ------------------------------------------------------------------ #

    def get_stats(self) -> Dict[str, int]:
        """Get download statistics."""
        return {
            'completed': self._completed_count,
            'failed': self._failed_count,
            'skipped': self._skipped_count,
        }

    def reset_stats(self) -> None:
        """Reset download statistics."""
        with self._download_lock:
            self._completed_count = 0
            self._failed_count = 0
            self._skipped_count = 0
            self._consecutive_timeouts = 0
            self._backend_switched = False


# Convenience function
def get_downloader(config: Config = None) -> YouTubeDownloader:
    """
    Create YouTubeDownloader instance.

    Args:
        config: Configuration object

    Returns:
        YouTubeDownloader instance
    """
    return YouTubeDownloader(config)

