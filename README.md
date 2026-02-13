# Exportify Downloader

Download your Spotify playlists as high-quality audio files. Export a playlist CSV from [Exportify](https://exportify.net/), then run one command.

## Quick Start

### 1. Install

```bash
# Install system deps
sudo apt install ffmpeg         # Ubuntu/Debian
sudo dnf install ffmpeg         # Fedora

# Install spotdl (download backend)
pip install spotdl

# Install this tool
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

That's it. The interactive wizard will find your CSV, let you pick options, and start downloading.

## Commands

| Command | What it does |
|---------|-------------|
| `exportifydl run` | Interactive mode — walks you through everything |
| `exportifydl download playlist.csv` | Download directly from a CSV file |
| `exportifydl preview playlist.csv` | Preview tracks without downloading |
| `exportifydl sample` | Generate a sample CSV to test with |

### Download Options

```bash
exportifydl download playlist.csv --output ~/Music --parallel 3 --skip-existing --create-lrc
```

| Flag | Description | Default |
|------|-------------|---------|
| `-o, --output` | Where to save files | `~/Music` |
| `-p, --parallel` | Simultaneous downloads | `3` |
| `-s, --skip-existing` | Skip already downloaded tracks | off |
| `-c, --create-lrc` | Generate synced lyrics files | off |
| `--dry-run` | Preview only, don't download | off |
| `-v, --verbose` | Show detailed output | off |

## How It Works

1. Parses your Exportify CSV to get track info (artist, title, album)
2. Uses [spotdl](https://github.com/spotDL/spotify-downloader) to find and download each track
3. Embeds metadata and album art automatically
4. Saves files organized by artist and album:

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
- [spotdl](https://github.com/spotDL/spotify-downloader) (primary) or yt-dlp (fallback)

## Troubleshooting

**Downloads failing?** Make sure spotdl is installed and working:
```bash
spotdl download "Metallica - Enter Sandman" --output /tmp/test
```

**ffmpeg not found?** Install it with your package manager (see install section above).

**Tracks being skipped?** Use `--skip-existing` only if you want to skip files you already have.

---

*For personal use only. Respect copyright and terms of service.*

