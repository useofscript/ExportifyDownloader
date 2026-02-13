# Exportify YouTube Downloader - Updated Project Plan

## Project Overview
A Python application for Linux that:
1. Reads Spotify playlist metadata from Exportify CSV files
2. Searches and downloads highest quality audio from YouTube
3. Organizes music with folder structure: ~/Music/Artist/Album/
4. Downloads album art (max 1200x1200 resolution)
5. Generates .LRC lyrics files
6. Full metadata tagging support
7. Progress bars, resume capability, and batch processing

## Architecture
```
exportify_downloader/
├── src/
│   ├── __init__.py
│   ├── csv_parser.py          # Exportify CSV parsing
│   ├── youtube_downloader.py  # yt-dlp wrapper with best quality
│   ├── metadata_handler.py    # Tags, album art, lyrics (.LRC)
│   ├── file_manager.py        # Folder structure, file naming
│   └── config.py              # Configuration & settings
├── tests/
│   ├── __init__.py
│   ├── test_csv_parser.py
│   ├── test_youtube_downloader.py
│   └── test_metadata_handler.py
├── data/
│   └── sample_exportify.csv   # Example Exportify format
├── requirements.txt           # Python dependencies
├── setup.py                   # Package setup
├── README.md                  # Documentation
└── main.py                    # CLI entry point
```

## Core Features & Requirements

### 1. CSV Parser (csv_parser.py)
- Parse Exportify CSV format:
  - Track Name, Artist Name, Album Name, Added By, Added At
- Validate CSV structure
- Extract search queries (Track + Artist)
- Support quoted fields with commas

### 2. YouTube Downloader (youtube_downloader.py)
- Use yt-dlp for best quality detection
- Auto-select highest quality audio stream
- Resume capability for interrupted downloads
- Progress bars with rich library
- Batch processing with concurrent downloads (default: 3 parallel)
- Skip already downloaded files (check by filename)
- Download lyrics from YouTube (if available)
- Extract thumbnail as album art

### 3. Metadata Handler (metadata_handler.py)
- Tag files with:
  - Artist, Album, Track Title
  - Track Number, Album Artist
  - Album Art (embedded and separate files)
  - Genre, Year, Comment
- Generate .LRC synced lyrics files
- Process album art to max 1200x1200 pixels
- Save album covers to album folder
- Save track covers to track folder

### 4. File Manager (file_manager.py)
- Folder structure:
  - ~/Music/[Artist]/[Album]/
  - ~/Music/[Artist]/[Album]/.covers/ (album covers)
  - ~/Music/[Artist]/[Album]/[Track]/.cover (track cover)
- File naming: "%artist% - %title%"
- Handle file conflicts (numbered suffixes)
- Check existing files before download
- Linux path handling (~ expansion)

### 5. Configuration (config.py)
- Output directory: ~/Music (default, configurable)
- Audio format: best available (yt-dlp auto-select)
- Audio quality: maximum available
- Image size: max 1200x1200
- Parallel downloads: 3 (configurable)
- Skip existing files: True (default)
- Create .LRC files: True (default)

## Dependencies (requirements.txt)
```
yt-dlp>=2024.0.0
pandas>=2.0.0
mutagen>=1.47.0
Pillow>=10.0.0
rich>=13.0.0
python-dotenv>=1.0.0
tqdm>=4.66.0
```

## Implementation Steps
1. Create project structure
2. Implement csv_parser.py (CSV reading)
3. Implement file_manager.py (folder/filename logic)
4. Implement youtube_downloader.py (yt-dlp wrapper)
5. Implement metadata_handler.py (tags, art, lyrics)
6. Implement config.py (configuration)
7. Create main.py (CLI interface)
8. Add sample CSV file
9. Write unit tests
10. Create README.md
11. Create setup.py for installation

## Sample CSV Format (Exportify)
```csv
Track Name,Artist Name,Album Name,Added By,Added At
"Shape of You","Ed Sheeran","÷ (Divide)","User","2024-01-15"
"Blinding Lights","The Weeknd","After Hours","User","2024-01-16"
```

## CLI Commands (main.py)
```bash
# Basic usage
python main.py playlist.csv

# With custom output directory
python main.py playlist.csv --output /path/to/music

# With parallel downloads
python main.py playlist.csv --parallel 5

# Verbose mode
python main.py playlist.csv --verbose

# Skip existing files
python main.py playlist.csv --skip-existing
```

## Success Criteria
✅ Reads Exportify CSV files correctly
✅ Auto-detects and downloads highest quality audio
✅ Skips already downloaded tracks
✅ Creates proper folder structure (Artist/Album/)
✅ Downloads and embeds album art (max 1200x1200)
✅ Generates .LRC lyrics files
✅ Shows progress bars during downloads
✅ Supports resume for interrupted downloads
✅ Batch processing with parallel downloads
✅ Full Linux compatibility
✅ No Spotify API required

## Quality Selection Logic
```python
# yt-dlp will auto-select best quality:
# 1. Check available audio formats
# 2. Prefer higher bitrate (320kbps > 256kbps > 128kbps)
# 3. Prefer better codec (m4a/aac > mp3 > opus > vorbis)
# 4. Select best format code automatically
```

## Album Art Processing
```python
# Image processing with Pillow:
# 1. Download thumbnail from YouTube
# 2. Resize to max 1200x1200 maintaining aspect ratio
# 3. Convert to JPEG format
# 4. Save 1200px version to album folder
# 5. Embed in audio file using mutagen
# 6. Save 1200px version to track folder
```

## Lyrics (.LRC) Format
```lrc
[00:00.00]Line 1
[00:05.50]Line 2
[00:10.25]Line 3
```
- Extract timestamps from YouTube description
- Generate synchronized lyrics file
- Save as .LRC in track folder

## Testing Strategy
1. CSV parsing with sample data
2. File path handling and creation
3. Metadata reading/writing
4. YouTube search and download
5. Album art processing
6. Full integration test with sample playlist

