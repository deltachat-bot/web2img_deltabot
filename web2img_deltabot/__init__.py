"""Bot to take website Screenshots"""
import asyncio

from .hooks import cli


def main() -> None:
    """Start the CLI application."""
    asyncio.run(cli.start())
