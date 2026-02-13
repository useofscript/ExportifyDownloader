"""
Metadata Handler for music files.
Handles audio tagging, album art embedding, and lyrics (.LRC) processing.
"""

import os
import re
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
from PIL import Image
from mutagen import File, FileType
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TPE2, TRCK, TYER, TDRC, TCON, COMM
from mutagen.mp4 import MP4
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
import logging


logger = logging.getLogger(__name__)


class MetadataHandler:
    """
    Handles all metadata operations for downloaded music files.
    
    Capabilities:
    - Read/write tags (ID3, M4A, FLAC)
    - Embed album art (max 1200x1200)
    - Generate .LRC lyrics files
    - Handle multiple audio formats
    """
    
    # Supported audio formats
    SUPPORTED_FORMATS = ['.m4a', '.mp3', '.flac', '.ogg', '.wav']
    
    # Image size constraints
    MAX_IMAGE_SIZE = 1200
    
    def __init__(self, max_image_size: int = 1200):
        """
        Initialize metadata handler.
        
        Args:
            max_image_size: Maximum dimension for album art (default: 1200)
        """
        self.max_image_size = max_image_size
    
    def process_metadata(self, audio_path: Path, metadata: Dict[str, Any],
                        album_art_path: Optional[Path] = None) -> bool:
        """
        Apply all metadata to an audio file.
        
        Args:
            audio_path: Path to audio file
            metadata: Dictionary with track metadata
            album_art_path: Optional path to album art
            
        Returns:
            True if successful
        """
        try:
            if not audio_path.exists():
                logger.error(f"Audio file not found: {audio_path}")
                return False
            
            # Get file type and apply appropriate tags
            ext = audio_path.suffix.lower()
            
            if ext == '.m4a':
                self._tag_m4a(audio_path, metadata, album_art_path)
            elif ext == '.mp3':
                self._tag_mp3(audio_path, metadata, album_art_path)
            elif ext == '.flac':
                self._tag_flac(audio_path, metadata, album_art_path)
            elif ext in ['.ogg', '.wav']:
                self._tag_vorbis(audio_path, metadata, album_art_path)
            else:
                logger.warning(f"Unsupported format: {ext}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing metadata for {audio_path}: {e}")
            return False
    
    def _tag_m4a(self, audio_path: Path, metadata: Dict[str, Any],
                 album_art_path: Optional[Path] = None) -> None:
        """
        Apply metadata to M4A/AAC file.
        
        Args:
            audio_path: Path to M4A file
            metadata: Track metadata
            album_art_path: Path to album art
        """
        try:
            audio = MP4(str(audio_path))
            
            # Create tags dict for mutagen
            tags = {}
            
            # Map metadata fields to M4A tags
            if metadata.get('title'):
                tags['\xa9nam'] = metadata['title']  # Title
            if metadata.get('artist'):
                tags['\xa9ART'] = metadata['artist']  # Artist
            if metadata.get('album'):
                tags['\xa9alb'] = metadata['album']  # Album
            if metadata.get('album_artist'):
                tags['aART'] = metadata['album_artist']  # Album Artist
            if metadata.get('track_number'):
                tags['trkn'] = [(int(metadata['track_number']), 0)]  # Track number
            if metadata.get('year'):
                tags['\xa9day'] = str(metadata['year'])  # Year
            if metadata.get('genre'):
                tags['\xa9gen'] = metadata['genre']  # Genre
            if metadata.get('comment'):
                tags['\xa9cmt'] = metadata['comment']  # Comment
            
            # Update tags
            for key, value in tags.items():
                audio[key] = value
            
            # Add album art if available
            if album_art_path and album_art_path.exists():
                self._embed_cover_m4a(audio, album_art_path)
            
            audio.save()
            
        except Exception as e:
            logger.error(f"Error tagging M4A: {e}")
            raise
    
    def _tag_mp3(self, audio_path: Path, metadata: Dict[str, Any],
                 album_art_path: Optional[Path] = None) -> None:
        """
        Apply metadata to MP3 file using ID3 tags.
        
        Args:
            audio_path: Path to MP3 file
            metadata: Track metadata
            album_art_path: Path to album art
        """
        try:
            audio = MP3(str(audio_path))
            
            if audio.tags is None:
                audio.add_tags()
            
            tags = audio.tags
            
            # Set ID3 tags
            if metadata.get('title'):
                tags.add(TIT2(encoding=3, text=metadata['title']))
            if metadata.get('artist'):
                tags.add(TPE1(encoding=3, text=metadata['artist']))
            if metadata.get('album'):
                tags.add(TALB(encoding=3, text=metadata['album']))
            if metadata.get('album_artist'):
                tags.add(TPE2(encoding=3, text=metadata['album_artist']))
            if metadata.get('track_number'):
                tags.add(TRCK(encoding=3, text=metadata['track_number']))
            if metadata.get('year'):
                tags.add(TDRC(encoding=3, text=str(metadata['year'])))
            if metadata.get('genre'):
                tags.add(TCON(encoding=3, text=metadata['genre']))
            if metadata.get('comment'):
                tags.add(COMM(encoding=3, lang='eng', desc='', text=metadata['comment']))
            
            # Add album art if available
            if album_art_path and album_art_path.exists():
                self._embed_cover_mp3(tags, album_art_path)
            
            audio.save()
            
        except Exception as e:
            logger.error(f"Error tagging MP3: {e}")
            raise
    
    def _tag_flac(self, audio_path: Path, metadata: Dict[str, Any],
                  album_art_path: Optional[Path] = None) -> None:
        """
        Apply metadata to FLAC file.
        
        Args:
            audio_path: Path to FLAC file
            metadata: Track metadata
            album_art_path: Path to album art
        """
        try:
            audio = FLAC(str(audio_path))
            
            if metadata.get('title'):
                audio['TITLE'] = metadata['title']
            if metadata.get('artist'):
                audio['ARTIST'] = metadata['artist']
            if metadata.get('album'):
                audio['ALBUM'] = metadata['album']
            if metadata.get('album_artist'):
                audio['ALBUMARTIST'] = metadata['album_artist']
            if metadata.get('track_number'):
                audio['TRACKNUMBER'] = str(metadata['track_number'])
            if metadata.get('year'):
                audio['DATE'] = str(metadata['year'])
            if metadata.get('genre'):
                audio['GENRE'] = metadata['genre']
            if metadata.get('comment'):
                audio['COMMENT'] = metadata['comment']
            
            # Add album art if available
            if album_art_path and album_art_path.exists():
                self._embed_cover_flac(audio, album_art_path)
            
            audio.save()
            
        except Exception as e:
            logger.error(f"Error tagging FLAC: {e}")
            raise
    
    def _tag_vorbis(self, audio_path: Path, metadata: Dict[str, Any],
                    album_art_path: Optional[Path] = None) -> None:
        """
        Apply metadata to OGG/Vorbis files.
        
        Args:
            audio_path: Path to OGG file
            metadata: Track metadata
            album_art_path: Path to album art
        """
        try:
            audio = File(str(audio_path))
            
            if metadata.get('title'):
                audio['TITLE'] = metadata['title']
            if metadata.get('artist'):
                audio['ARTIST'] = metadata['artist']
            if metadata.get('album'):
                audio['ALBUM'] = metadata['album']
            if metadata.get('album_artist'):
                audio['ALBUMARTIST'] = metadata['album_artist']
            if metadata.get('track_number'):
                audio['TRACKNUMBER'] = str(metadata['track_number'])
            if metadata.get('year'):
                audio['DATE'] = str(metadata['year'])
            if metadata.get('genre'):
                audio['GENRE'] = metadata['genre']
            if metadata.get('comment'):
                audio['COMMENT'] = metadata['comment']
            
            # OGG doesn't support embedded images easily with mutagen
            # Album art will be saved separately
            
            audio.save()
            
        except Exception as e:
            logger.error(f"Error tagging OGG: {e}")
            raise
    
    def _embed_cover_m4a(self, audio: MP4, cover_path: Path) -> None:
        """
        Embed album art in M4A file.
        
        Args:
            audio: MP4 file object
            cover_path: Path to cover image
        """
        try:
            with open(cover_path, 'rb') as f:
                cover_data = f.read()
            
            # Add cover to M4A
            audio['covr'] = [cover_data]
            
        except Exception as e:
            logger.warning(f"Could not embed cover in M4A: {e}")
    
    def _embed_cover_mp3(self, tags: ID3, cover_path: Path) -> None:
        """
        Embed album art in MP3 file using APIC frame.
        
        Args:
            tags: ID3 tags object
            cover_path: Path to cover image
        """
        try:
            from mutagen.id3 import APIC
            
            with open(cover_path, 'rb') as f:
                cover_data = f.read()
            
            # Determine MIME type
            if cover_path.suffix.lower() in ['.jpg', '.jpeg']:
                mime = 'image/jpeg'
            else:
                mime = 'image/png'
            
            # Add APIC frame
            tags.add(APIC(
                encoding=3,
                mime=mime,
                type=3,  # Cover (front)
                desc='Cover',
                data=cover_data
            ))
            
        except Exception as e:
            logger.warning(f"Could not embed cover in MP3: {e}")
    
    def _embed_cover_flac(self, audio: FLAC, cover_path: Path) -> None:
        """
        Embed album art in FLAC file.
        
        Args:
            audio: FLAC file object
            cover_path: Path to cover image
        """
        try:
            with open(cover_path, 'rb') as f:
                cover_data = f.read()
            
            # Add picture to FLAC
            picture = FLAC.Picture()
            picture.data = cover_data
            
            # Set picture type
            picture.type = 3  # Cover (front)
            
            # Set MIME type
            if cover_path.suffix.lower() in ['.jpg', '.jpeg']:
                picture.mime = 'image/jpeg'
            else:
                picture.mime = 'image/png'
            
            audio.add_picture(picture)
            
        except Exception as e:
            logger.warning(f"Could not embed cover in FLAC: {e}")
    
    def process_album_art(self, source_path: Path, 
                         output_path: Optional[Path] = None,
                         max_size: int = None) -> Optional[Path]:
        """
        Process album art: resize and save.
        
        Args:
            source_path: Path to source image
            output_path: Optional output path
            max_size: Maximum dimension (default from config)
            
        Returns:
            Path to processed image
        """
        if max_size is None:
            max_size = self.max_image_size
        
        try:
            with Image.open(source_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[3])
                    else:
                        background.paste(img)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize maintaining aspect ratio
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Determine output path
                if output_path is None:
                    output_path = source_path.with_suffix('.jpg')
                
                # Ensure output directory exists
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Save as JPEG
                img.save(output_path, 'JPEG', quality=95, optimize=True)
                
                return output_path
                
        except Exception as e:
            logger.error(f"Error processing album art: {e}")
            return None
    
    def extract_thumbnail(self, video_path: str) -> Optional[Path]:
        """
        Extract thumbnail from video file using ffprobe.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Path to extracted thumbnail
        """
        import subprocess
        
        # Output path for thumbnail
        thumb_path = Path(video_path).with_suffix('.jpg')
        
        try:
            # Use ffmpeg to extract frame
            cmd = [
                'ffmpeg', '-y',
                '-ss', '00:00:02',  # Seek to 2 seconds
                '-i', video_path,
                '-vframes', '1',
                '-q:v', '2',  # High quality
                str(thumb_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            
            if result.returncode == 0 and thumb_path.exists():
                return self.process_album_art(thumb_path)
            
            return None
            
        except Exception as e:
            logger.warning(f"Could not extract thumbnail: {e}")
            return None
    
    def download_album_art(self, url: str, output_path: Path) -> Optional[Path]:
        """
        Download album art from URL.
        
        Args:
            url: Image URL
            output_path: Path to save image
            
        Returns:
            Path to downloaded image
        """
        import urllib.request
        
        try:
            # Set headers to avoid 403 errors
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=30) as response:
                image_data = response.read()
            
            # Save to temp file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'wb') as f:
                f.write(image_data)
            
            # Process the image
            return self.process_album_art(output_path)
            
        except Exception as e:
            logger.warning(f"Could not download album art: {e}")
            return None
    
    def create_lrc_file(self, lyrics: str, output_path: Path,
                       artist: str = "", title: str = "") -> Path:
        """
        Create LRC (synced lyrics) file.
        
        Args:
            lyrics: Lyrics content (plain or with timestamps)
            output_path: Path to save LRC file
            artist: Artist name (for header)
            title: Track title (for header)
            
        Returns:
            Path to created file
        """
        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Build LRC content
            lrc_lines = []
            
            # Add metadata header
            lrc_lines.append("[ti:" + title + "]")
            lrc_lines.append("[ar:" + artist + "]")
            lrc_lines.append("")
            
            # Process lyrics
            if lyrics:
                for line in lyrics.strip().split('\n'):
                    line = line.strip()
                    if line:
                        # Check if line already has timestamp
                        if not self._has_timestamp(line):
                            # Add empty timestamp
                            lrc_lines.append("[00:00.00]" + line)
                        else:
                            lrc_lines.append(line)
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lrc_lines))
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error creating LRC file: {e}")
            raise
    
    def _has_timestamp(self, line: str) -> bool:
        """
        Check if line already has LRC timestamp.
        
        Args:
            line: Lyrics line
            
        Returns:
            True if timestamp present
        """
        pattern = r'\[\d{2}:\d{2}\.\d{2,3}\]'
        return bool(re.search(pattern, line))
    
    def parse_lrc_file(self, lrc_path: Path) -> Dict[float, str]:
        """
        Parse LRC file and extract timed lyrics.
        
        Args:
            lrc_path: Path to LRC file
            
        Returns:
            Dictionary with timestamp (seconds) -> lyrics
        """
        timed_lyrics = {}
        
        if not lrc_path.exists():
            return timed_lyrics
        
        try:
            with open(lrc_path, 'r', encoding='utf-8') as f:
                for line in f.readlines():
                    line = line.strip()
                    
                    # Extract timestamp
                    pattern = r'\[(\d{2}):(\d{2})\.(\d{2,3})\]'
                    match = re.search(pattern, line)
                    
                    if match:
                        minutes = int(match.group(1))
                        seconds = int(match.group(2))
                        milliseconds = match.group(3)
                        
                        # Calculate total seconds
                        total_seconds = minutes * 60 + seconds + int(milliseconds) / 100
                        
                        # Extract lyrics text
                        lyrics_text = re.sub(pattern, '', line).strip()
                        
                        if lyrics_text:
                            timed_lyrics[total_seconds] = lyrics_text
            
        except Exception as e:
            logger.warning(f"Could not parse LRC file: {e}")
        
        return timed_lyrics
    
    def read_metadata(self, audio_path: Path) -> Dict[str, Any]:
        """
        Read existing metadata from audio file.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary with metadata
        """
        metadata = {}
        
        if not audio_path.exists():
            return metadata
        
        try:
            ext = audio_path.suffix.lower()
            
            if ext == '.m4a':
                audio = MP4(str(audio_path))
                mapping = {
                    '\xa9nam': 'title',
                    '\xa9ART': 'artist',
                    '\xa9alb': 'album',
                    'aART': 'album_artist',
                    '\xa9day': 'year',
                    '\xa9gen': 'genre',
                }
                for src, dst in mapping.items():
                    if src in audio:
                        metadata[dst] = audio[src]
            
            elif ext == '.mp3':
                audio = MP3(str(audio_path))
                if audio.tags:
                    tags = audio.tags
                    if 'TIT2' in tags:
                        metadata['title'] = str(tags['TIT2'])
                    if 'TPE1' in tags:
                        metadata['artist'] = str(tags['TPE1'])
                    if 'TALB' in tags:
                        metadata['album'] = str(tags['TALB'])
            
            elif ext == '.flac':
                audio = FLAC(str(audio_path))
                for field in ['TITLE', 'ARTIST', 'ALBUM', 'DATE', 'GENRE']:
                    if field in audio:
                        metadata[field.lower()] = str(audio[field])
            
        except Exception as e:
            logger.warning(f"Could not read metadata: {e}")
        
        return metadata


# Convenience function
def get_metadata_handler(max_image_size: int = 1200) -> MetadataHandler:
    """
    Create MetadataHandler instance.
    
    Args:
        max_image_size: Maximum album art dimension
        
    Returns:
        MetadataHandler instance
    """
    return MetadataHandler(max_image_size)

