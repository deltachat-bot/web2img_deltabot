"""Bot to take website Screenshots"""
from .hooks import cli


def main() -> None:
    """Start the CLI application."""
    try:
        cli.start()
    except KeyboardInterrupt:
        pass
