# Exportify YouTube Downloader

A powerful Linux application to download music from YouTube using Spotify playlist CSV exports. No Spotify API required!

## Features

- 📥 **CSV Parsing**: Read Exportify CSV files containing Spotify playlist metadata
- 🎵 **Best Quality Audio**: Automatically detects and downloads highest quality audio
- 🖼️ **Album Art**: Downloads and embeds album art (max 1200x1200 resolution)
- 📝 **Lyrics**: Generates .LRC synced lyrics files
- 📁 **Organized Library**: Creates proper folder structure: `~/Music/Artist/Album/`
- ⏸️ **Resume Capability**: Handles interrupted downloads gracefully
- 🚀 **Batch Processing**: Parallel downloads with configurable concurrency
- ⏭️ **Skip Existing**: Automatically skips already downloaded tracks
- 🏷️ **Full Metadata**: Complete ID3/AIFF/Vorbis tagging support
- 📊 **Progress Tracking**: Beautiful progress bars with rich library
- 🔧 **Linux Native**: Full path handling for Linux systems

## Requirements

- **Python 3.9+**
- **ffmpeg** (for audio processing)
- **yt-dlp** (for YouTube downloading)
- **Linux** (tested on Ubuntu, Debian, Fedora)

## Installation

### 1. Install System Dependencies

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg python3-pip

# Fedora/RHEL
sudo dnf install ffmpeg python3-pip

# Arch Linux
sudo pacman -S ffmpeg python-pip
```

### 2. Install Python Dependencies

```bash
# Clone or navigate to project directory
cd exportify_downloader

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Optional: Install as Package

```bash
pip install -e .
```

This installs `exportify-downloader` command.

## Usage

### Basic Usage

```bash
python main.py playlist.csv
```

### With Custom Output Directory

```bash
python main.py playlist.csv --output /path/to/music
```

### Parallel Downloads

```bash
python main.py playlist.csv --parallel 5
```

### Verbose Mode

```bash
python main.py playlist.csv --verbose
```

### Dry Run (Preview Only)

```bash
python main.py playlist.csv --dry-run
```

### Generate Sample CSV

```bash
python main.py --sample
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `csv_file` | Path to Exportify CSV file |
| `-o, --output` | Output directory (default: ~/Music) |
| `-p, --parallel` | Parallel downloads (default: 3) |
| `-v, --verbose` | Verbose output |
| `-s, --skip-existing` | Skip existing files |
| `-c, --create-lrc` | Create LRC lyrics files |
| `--dry-run` | Preview without downloading |
| `--sample` | Generate sample CSV |
| `--config` | Path to config JSON file |

## CSV Format

The tool expects CSV files in Exportify format:

```csv
Track Name,Artist Name,Album Name,Added By,Added At
"Shape of You","Ed Sheeran","÷ (Divide)","user1","2024-01-15"
"Blinding Lights","The Weeknd","After Hours","user1","2024-01-16"
```

### Required Columns
- `Track Name` - Title of the track
- `Artist Name` - Artist name
- `Album Name` - Album name

### Optional Columns
- `Added By` - User who added the track
- `Added At` - Date added

## File Structure

Downloaded music is organized as:

```
~/Music/
└── Artist Name/
    └── Album Name/
        ├── Track Name.m4a
        ├── Track Name.lrc
        └── .covers/
            └── album.jpg
```

### File Naming
- Audio files: `{Artist} - {Title}.m4a`
- LRC files: `{Title}.lrc`
- Album art: `.covers/album.jpg`
- Track art: `.{Title}.cover.jpg`

## Configuration

### Environment Variables

```bash
export EXPORTIFY_OUTPUT_DIR="~/Music"
export EXPORTIFY_PARALLEL=3
export EXPORTIFY_SKIP_EXISTING=true
export EXPORTIFY_CREATE_LRC=true
export EXPORTIFY_ALBUM_ART_SIZE=1200
export EXPORTIFY_VERBOSE=false
export EXPORTIFY_TIMEOUT=300
export EXPORTIFY_RETRIES=3
```

### Config File

Create `~/.config/exportify_downloader/config.json`:

```json
{
    "output_dir": "~/Music",
    "parallel_downloads": 3,
    "skip_existing": true,
    "create_lrc": true,
    "album_art_size": 1200,
    "audio_format": "best",
    "verbose": false,
    "download_timeout": 300,
    "max_retries": 3
}
```

## Quality Selection

The downloader automatically selects the best available quality:

1. **Audio Codec**: m4a/aac (best quality per bitrate)
2. **Bitrate**: Highest available (320kbps preferred)
3. **Format**: yt-dlp auto-selects best format

## Dependencies

### Python Packages
- `yt-dlp` - YouTube downloading
- `pandas` - CSV handling
- `mutagen` - Audio metadata
- `Pillow` - Image processing
- `rich` - Terminal output
- `python-dotenv` - Configuration
- `tqdm` - Progress bars

### System Packages
- `ffmpeg` - Audio encoding/decoding

## Troubleshooting

### FFmpeg Not Found
```bash
which ffmpeg
# If not found, install ffmpeg
sudo apt install ffmpeg  # Ubuntu/Debian
```

### Download Errors
```bash
# Try with verbose mode
python main.py playlist.csv --verbose
```

### Permission Denied
```bash
# Ensure output directory is writable
chmod 755 ~/Music
```

### Slow Downloads
```bash
# Reduce parallel downloads
python main.py playlist.csv --parallel 1
```

## Exportify CSV Export

To get your Spotify playlists as CSV:

1. Go to [Exportify](https://exportify.net/)
2. Login with Spotify
3. Select your playlist
4. Click "Export Playlist"
5. Save the CSV file

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

- Report issues on GitHub
- Check troubleshooting section first
- Enable verbose mode for debug info

---

**Note**: This tool is for personal use only. Respect copyright and YouTube's terms of service. Download only music you have rights to access.

