#!/usr/bin/env python3
"""
Exportify YouTube Downloader - Main Entry Point

A tool to download music from YouTube based on Spotify playlist CSV exports.
No Spotify API required - just CSV parsing and YouTube downloading.

Usage (interactive):
    python main.py
    ./run.sh

Usage (command line):
    python main.py playlist.csv
    python main.py playlist.csv --output ~/Music
    python main.py playlist.csv --parallel 5
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt, Confirm, IntPrompt
from rich import box

from src.csv_parser import parse_csv, ExportifyCSVParser
from src.youtube_downloader import YouTubeDownloader
from src.config import Config, get_config, reset_config
from src.file_manager import FileManager


console = Console()


def print_banner():
    """Print application banner."""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   Exportify YouTube Downloader                           ║
    ║   Download Spotify playlists from YouTube                 ║
    ║   No Spotify API required!                               ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    console.print(Panel(
        Text(banner, justify="center", style="cyan bold"),
        box=box.ROUNDED,
        style="cyan",
    ))


def print_playlist_info(playlist) -> None:
    """Print playlist information."""
    table = Table(title="Playlist Info", show_header=True, header_style="bold magenta")
    table.add_column("Property", style="dim")
    table.add_column("Value", style="green")
    
    table.add_row("Name", playlist.name)
    table.add_row("Total Tracks", str(len(playlist)))
    table.add_row("Unique Artists", str(len(playlist.get_artists())))
    table.add_row("Unique Albums", str(len(playlist.get_albums())))
    
    console.print(table)


def print_download_summary(results: List[dict], elapsed_time: float) -> None:
    """Print download summary."""
    successful = sum(1 for r in results if r.get('success'))
    failed = sum(1 for r in results if not r.get('success'))
    skipped = sum(1 for r in results if r.get('skipped'))
    
    table = Table(title="Download Summary", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="dim")
    table.add_column("Count", style="green")
    
    table.add_row("Total Tracks", str(len(results)))
    table.add_row("Successful", str(successful))
    table.add_row("Failed", str(failed) if failed else "[green]0[/green]")
    table.add_row("Skipped", str(skipped) if skipped else "[green]0[/green]")
    table.add_row("Time Elapsed", f"{elapsed_time:.1f}s")
    
    console.print(table)
    
    if failed > 0:
        console.print("\n[yellow]Failed downloads:[/yellow]")
        for r in results:
            if not r.get('success') and not r.get('skipped'):
                console.print(f"  • {r.get('artist', 'Unknown')} - {r.get('title', 'Unknown')}")
                console.print(f"    [red]Error: {r.get('error', 'Unknown error')}[/red]")


def ask_yn(question: str, default: bool = True) -> bool:
    """Ask a yes/no question with a default."""
    return Confirm.ask(f"[cyan]{question}[/cyan]", default=default)


def find_csv_files() -> List[Path]:
    """Find CSV files in current directory, subdirectories (1 level deep), and home."""
    files = []
    for pattern in ['*.csv', '*/*.csv']:
        files.extend(Path('.').glob(pattern))
    # Also check ~/Downloads and ~/Desktop
    for extra in [Path.home() / 'Downloads', Path.home() / 'Desktop']:
        if extra.exists():
            files.extend(extra.glob('*.csv'))
    return sorted(set(files))


def interactive_mode() -> int:
    """Run in interactive question-based mode."""
    print_banner()
    console.print("[bold green]Interactive Setup[/bold green]\n")

    # Step 1: Get CSV file path
    csv_files = find_csv_files()

    if csv_files:
        console.print("[dim]CSV files found nearby:[/dim]")
        for i, f in enumerate(csv_files, 1):
            console.print(f"  [cyan]{i}.[/cyan] {f}")
        console.print()

    csv_path_str = Prompt.ask(
        "[cyan]Pick a number or type a path[/cyan]",
        default="1" if csv_files else None,
    )
    csv_path_str = csv_path_str.strip().strip("'\"")

    # If the user typed a number, map it to the corresponding file
    if csv_path_str.isdigit() and csv_files:
        idx = int(csv_path_str)
        if 1 <= idx <= len(csv_files):
            csv_path = csv_files[idx - 1]
        else:
            console.print(f"\n[red]Invalid choice: {idx}[/red] (pick 1-{len(csv_files)})")
            return 1
    else:
        csv_path = Path(csv_path_str)
    if not csv_path.exists():
        console.print(f"\n[red]File not found: {csv_path}[/red]")
        console.print("[dim]Export your playlist from https://exportify.net first.[/dim]")
        return 1

    # Parse CSV and show info
    console.print()
    try:
        playlist = parse_csv(str(csv_path))
        print_playlist_info(playlist)
    except Exception as e:
        console.print(f"[red]Error reading CSV: {e}[/red]")
        return 1

    # Step 2: Output directory
    console.print()
    output_dir = Prompt.ask(
        "[cyan]Where to save music?[/cyan]",
        default="~/Music",
    ).strip()

    # Step 3: Organize into folders?
    organize = ask_yn("Organize into Artist/Album folders?", default=True)

    # Step 4: Skip existing?
    skip_existing = ask_yn("Skip already downloaded songs?", default=True)

    # Step 5: Overwrite?
    if not skip_existing:
        console.print("  [dim](Existing files will be re-downloaded)[/dim]")

    # Step 6: Download lyrics?
    create_lrc = ask_yn("Download lyrics (.LRC files)?", default=True)

    # Step 7: Parallel downloads
    parallel = IntPrompt.ask(
        "[cyan]How many songs to download at once?[/cyan]",
        default=3,
    )
    parallel = max(1, min(parallel, 30))

    # Step 8: Preview first?
    console.print()
    preview = ask_yn("Preview track list before downloading?", default=True)

    if preview:
        console.print("\n[bold]Track list:[/bold]")
        for i, track in enumerate(playlist.tracks, 1):
            console.print(f"  [dim]{i:3}.[/dim] {track.artist_name} - {track.track_name}")
        console.print()

        if not ask_yn(f"Download all {len(playlist)} tracks?", default=True):
            console.print("[yellow]Cancelled.[/yellow]")
            return 0

    # Configure and run
    reset_config()
    config = get_config()
    config.output_dir = output_dir
    config.parallel_downloads = parallel
    config.skip_existing = skip_existing
    config.create_lrc = create_lrc

    if not organize:
        config._settings["folder_structure"] = ""

    # Show summary
    console.print()
    summary = Table(title="Ready to Download", show_header=False, box=box.SIMPLE)
    summary.add_column(style="dim")
    summary.add_column(style="green")
    summary.add_row("Tracks", str(len(playlist)))
    summary.add_row("Save to", str(config.output_dir))
    summary.add_row("Folders", "Artist/Album/" if organize else "Flat")
    summary.add_row("Skip existing", "Yes" if skip_existing else "No")
    summary.add_row("Lyrics", "Yes" if create_lrc else "No")
    summary.add_row("Parallel", str(parallel))
    console.print(summary)
    console.print()

    return run_download(playlist, config)


def cli_mode(args) -> int:
    """Run in traditional CLI mode with arguments."""
    print_banner()

    # Validate CSV
    csv_path = Path(args.csv_file)
    if not csv_path.exists():
        console.print(f"[red]Error: CSV file not found: {csv_path}[/red]")
        console.print(f"[dim]Tip: Run 'exportifydl sample' to generate a sample CSV file[/dim]")
        return 1

    if csv_path.suffix.lower() != '.csv':
        console.print("[yellow]Warning: File doesn't have .csv extension[/yellow]")

    # Load configuration
    config = get_config(args.config)

    if args.output:
        config.output_dir = args.output
    if args.parallel:
        config.parallel_downloads = args.parallel
    if args.verbose:
        config.verbose = True
    if args.no_skip_existing:
        config.skip_existing = False
    if args.no_lrc:
        config.create_lrc = False

    # Show config
    console.print(f"\n[cyan]Output Directory:[/cyan] {config.output_dir}")
    console.print(f"[cyan]Parallel Downloads:[/cyan] {config.parallel_downloads}")
    console.print(f"[cyan]Skip Existing:[/cyan] {config.skip_existing}")
    console.print(f"[cyan]Create LRC Files:[/cyan] {config.create_lrc}")

    # Parse CSV
    console.print(f"\n[cyan]Parsing CSV file...[/cyan]")
    try:
        playlist = parse_csv(str(csv_path))
        print_playlist_info(playlist)
    except Exception as e:
        console.print(f"[red]Error parsing CSV: {e}[/red]")
        return 1

    # Dry run mode
    if args.dry_run:
        console.print("\n[yellow]Dry run mode - showing tracks without downloading:[/yellow]")
        for i, track in enumerate(playlist.tracks, 1):
            console.print(f"  {i:3}. {track.artist_name} - {track.track_name}")
        return 0

    return run_download(playlist, config)


def run_download(playlist, config) -> int:
    """Execute the download with given playlist and config."""
    downloader = YouTubeDownloader(config)

    download_tracks = [
        {
            'artist': track.artist_name,
            'album': track.album_name,
            'title': track.track_name,
            'search_query': track.get_search_query(),
        }
        for track in playlist.tracks
    ]

    console.print(f"[cyan]Downloading {len(download_tracks)} tracks...[/cyan]\n")
    start_time = datetime.now()

    try:
        results = downloader.download_batch(
            download_tracks,
            progress_callback=lambda current, total: None,
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")
        return 1

    elapsed_time = (datetime.now() - start_time).total_seconds()

    if results:
        print_download_summary(results, elapsed_time)

    console.print(f"\n[green]Downloads saved to:[/green] {config.output_dir}")
    return 0


def main():
    """Main entry point with subcommands."""
    # If called with no args, show the main help screen
    parser = argparse.ArgumentParser(
        prog="exportifydl",
        description="Exportify YouTube Downloader - Download music from YouTube using Spotify playlist CSV exports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", title="Commands")

    # --- run: interactive setup ---
    run_parser = subparsers.add_parser(
        "run", help="Start interactive setup (recommended)",
        description="Launch the interactive step-by-step setup wizard.",
    )

    # --- download: CLI download with a CSV ---
    dl_parser = subparsers.add_parser(
        "download", help="Download tracks from a CSV file",
        aliases=["dl"],
        description="Download tracks directly using command-line options.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  exportifydl download playlist.csv
  exportifydl download playlist.csv --output /path/to/music
  exportifydl download playlist.csv --parallel 5 --dry-run
        """,
    )
    dl_parser.add_argument('csv_file', type=str,
                           help='Path to Exportify CSV file')
    dl_parser.add_argument('-o', '--output', type=str, default=None,
                           help='Output directory (default: ~/Music)')
    dl_parser.add_argument('-p', '--parallel', type=int, default=None,
                           help='Number of parallel downloads (default: 3)')
    dl_parser.add_argument('-v', '--verbose', action='store_true',
                           help='Verbose output')
    dl_parser.add_argument('--no-skip-existing', action='store_true',
                           help='Re-download files that already exist')
    dl_parser.add_argument('--no-lrc', action='store_true',
                           help='Disable LRC lyrics file generation')
    dl_parser.add_argument('--dry-run', action='store_true',
                           help='Preview tracks without downloading')
    dl_parser.add_argument('--config', type=str, default=None,
                           help='Path to config JSON file')

    # --- sample: generate sample CSV ---
    sample_parser = subparsers.add_parser(
        "sample", help="Generate a sample CSV file to try out",
        description="Create a sample Exportify CSV with example tracks.",
    )
    sample_parser.add_argument('-o', '--output', type=str, default="sample_playlist.csv",
                               help='Output filename (default: sample_playlist.csv)')

    # --- preview: quick dry-run ---
    preview_parser = subparsers.add_parser(
        "preview", help="Preview tracks in a CSV without downloading",
        description="Parse a CSV and list all tracks.",
    )
    preview_parser.add_argument('csv_file', type=str,
                                help='Path to Exportify CSV file')

    args = parser.parse_args()

    # No command given → show welcome + usage
    if not args.command:
        print_banner()
        console.print("[bold green]Welcome to Exportify YouTube Downloader![/bold green]\n")
        console.print("Commands:")
        console.print("  [cyan]exportifydl run[/cyan]                    Start interactive setup (recommended)")
        console.print("  [cyan]exportifydl download[/cyan] [dim]<file.csv>[/dim]   Download from CSV directly")
        console.print("  [cyan]exportifydl preview[/cyan]  [dim]<file.csv>[/dim]   Preview tracks in a CSV")
        console.print("  [cyan]exportifydl sample[/cyan]                 Generate a sample CSV to try")
        console.print("  [cyan]exportifydl --help[/cyan]                 Show detailed help\n")

        csv_files = find_csv_files()
        if csv_files:
            console.print("[dim]CSV files found nearby:[/dim]")
            for f in csv_files:
                console.print(f"  • [cyan]{f}[/cyan]")
            console.print()

        console.print("[dim]Get started:[/dim]  [cyan]exportifydl run[/cyan]")
        return 0

    # Handle commands
    if args.command == "run":
        try:
            return interactive_mode()
        except KeyboardInterrupt:
            console.print("\n[yellow]Cancelled.[/yellow]")
            return 0

    elif args.command in ("download", "dl"):
        return cli_mode(args)

    elif args.command == "sample":
        print_banner()
        sample_csv = ExportifyCSVParser().get_sample_csv()
        sample_path = Path(args.output)
        with open(sample_path, 'w', encoding='utf-8') as f:
            f.write(sample_csv)
        console.print(f"[green]Sample CSV saved to: {sample_path.resolve()}[/green]")
        console.print(f"\n[dim]Next steps:[/dim]")
        console.print(f"  [cyan]exportifydl preview {sample_path}[/cyan]   Preview the tracks")
        console.print(f"  [cyan]exportifydl run[/cyan]                    Start downloading")
        return 0

    elif args.command == "preview":
        print_banner()
        csv_path = Path(args.csv_file)
        if not csv_path.exists():
            console.print(f"[red]File not found: {csv_path}[/red]")
            return 1
        try:
            playlist = parse_csv(str(csv_path))
            print_playlist_info(playlist)
            console.print()
            for i, track in enumerate(playlist.tracks, 1):
                console.print(f"  [dim]{i:3}.[/dim] {track.artist_name} - {track.track_name}")
            console.print(f"\n[dim]To download:[/dim]  [cyan]exportifydl run[/cyan]")
        except Exception as e:
            console.print(f"[red]Error reading CSV: {e}[/red]")
            return 1
        return 0

    return 0


if __name__ == '__main__':
    sys.exit(main())

