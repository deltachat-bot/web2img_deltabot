"""Bot to take website Screenshots"""
import asyncio

from .hooks import cli


def main() -> None:
    """Start the CLI application."""
    try:
        asyncio.run(cli.start())
    except KeyboardInterrupt:
        pass
