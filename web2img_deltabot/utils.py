"""Utilities"""

import re
from argparse import Namespace
from pathlib import Path
from typing import Optional

url_regex = re.compile(
    r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
)


def get_url(text: str) -> Optional[str]:
    """Extract URL from text."""
    match = url_regex.search(text)
    if match:
        return match.group()
    return None


def take_screenshot(page, cfg: Namespace, path: Path) -> int:
    def _take_screenshot() -> int:
        return len(
            page.screenshot(
                path=path,
                type=cfg.img_type,
                quality=cfg.quality,
                scale=cfg.scale,
                omit_background=cfg.omit_background,
                full_page=cfg.full_page,
            )
        )

    size = _take_screenshot()

    cfg.img_type = "jpeg"
    cfg.omit_background = False
    while size > 1024**2 * 1 and cfg.quality >= 40:
        cfg.quality -= 10
        size = _take_screenshot()
    return size
