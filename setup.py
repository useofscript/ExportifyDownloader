"""
Setup configuration for Exportify YouTube Downloader.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="exportify_downloader",
    version="1.0.0",
    author="Exportify Downloader Team",
    description="Download music from YouTube using Spotify playlist CSV exports",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/exportify-downloader/exportify_downloader",
    packages=["src"],
    python_requires=">=3.9",
    install_requires=[
        "yt-dlp>=2024.0.0",
        "spotdl>=4.0.0",
        "mutagen>=1.47.0",
        "Pillow>=10.0.0",
        "rich>=13.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "exportifydl=src.cli:cli",
        ],
    },
    classifiers=[
        "Development Status :: 7 - Inactive",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Multimedia :: Sound/Audio :: Conversion",
        "Topic :: Multimedia :: Sound/Audio :: Downloaders",
    ],
    keywords=[
        "spotify", "youtube", "music", "download", "playlist", "csv",
        "exportify", "ffmpeg", "yt-dlp", "audio", "mp3", "m4a",
    ],
    project_urls={
        "Bug Reports": "https://github.com/exportify-downloader/exportify_downloader/issues",
        "Source": "https://github.com/exportify-downloader/exportify_downloader",
        "Documentation": "https://github.com/exportify-downloader/exportify_downloader#readme",
    },
)
