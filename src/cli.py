"""CLI entry point for exportifydl command."""

import sys
import os

# Ensure the project root is on the path so 'src' and 'main' can be imported
# cli.py is in src/, so project root is one level up
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def cli():
    """Entry point for the exportifydl console script."""
    from main import main
    sys.exit(main())


if __name__ == "__main__":
    cli()
