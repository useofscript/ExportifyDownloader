# Exportify Downloader

Download your Spotify playlists as high-quality audio files. Export a playlist CSV from [Exportify](https://exportify.net/), then run one command.

## Quick Start

### 1. Install

```bash
# Install system deps
sudo apt install ffmpeg         # Ubuntu/Debian
sudo dnf install ffmpeg         # Fedora

# Install the tool (pulls in spotdl + yt-dlp automatically)
git clone https://github.com/useofscript/Exportify-Linux.git
cd Exportify-Linux
pip install -e .
```

### 2. Export Your Playlist

1. Go to [exportify.net](https://exportify.net/)
2. Log in with Spotify
3. Click **Export** on any playlist
4. Save the `.csv` file

### 3. Download

```bash
exportifydl run
```

That's it. The interactive wizard will find your CSV, let you pick options, and start downloading. Failed tracks can be retried at the end.

## Commands

| Command | What it does |
|---------|-------------|
| `exportifydl run` | Interactive mode — walks you through everything |
| `exportifydl download playlist.csv` | Download directly from a CSV file |
| `exportifydl preview playlist.csv` | Preview tracks without downloading |
| `exportifydl sample` | Generate a sample CSV to test with |

### Download Options

```bash
exportifydl download playlist.csv --output ~/Music --parallel 6
```

| Flag | Description | Default |
|------|-------------|---------|
| `-o, --output` | Where to save files | `~/Music` |
| `-p, --parallel` | Simultaneous downloads | `4` |
| `--no-skip-existing` | Re-download files that already exist | skip on |
| `--no-lrc` | Disable lyrics (.lrc) file generation | lyrics on |
| `--no-folders` | Save all files flat (no Artist/Album dirs) | folders on |
| `--dry-run` | Preview only, don't download | off |
| `-v, --verbose` | Show detailed output | off |
| `--config` | Path to a config JSON file | none |

## How It Works

1. Parses your Exportify CSV to get track info (artist, title, album)
2. Uses [spotdl](https://github.com/spotDL/spotify-downloader) as the primary backend to download each track
3. Automatically falls back to [yt-dlp](https://github.com/yt-dlp/yt-dlp) if spotdl is rate-limited
4. Embeds metadata and album art automatically
5. After downloading, prompts to retry any failed tracks
6. Saves files organized by artist and album:

```
~/Music/
  Artist/
    Album/
      Artist - Track.m4a
      Track.lrc
```

## Requirements

- Python 3.9+
- ffmpeg
- [spotdl](https://github.com/spotDL/spotify-downloader) (primary backend)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) (fallback backend)

Both backends are installed automatically via `pip install -e .`

## Troubleshooting

**spotdl rate-limited?** The tool will automatically switch to yt-dlp. The spotdl cooldown resets after 24 hours.

**Age-restricted YouTube videos?** Some tracks fail because YouTube requires sign-in. These cannot be downloaded without browser cookies.

**ffmpeg not found?** Install it with your package manager (see install section above).

**Want to re-download everything?** Use `--no-skip-existing` to overwrite files you already have.

---

*For personal use only. Respect copyright and terms of service.*

