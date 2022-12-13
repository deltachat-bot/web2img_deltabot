"""Utilities"""
import re
from argparse import Namespace
from typing import Optional

from sqlalchemy.future import select

from .orm import User, async_session

url_regex = re.compile(
    r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
)


def get_url(text: str) -> Optional[str]:
    """Extract URL from text."""
    match = url_regex.search(text)
    if match:
        return match.group()
    return None


async def get_settings(contact_id) -> Namespace:
    """Get user settings."""
    stmt = select(User).filter(User.id == contact_id)
    async with async_session() as session:
        user = (await session.execute(stmt)).scalars().first()
        settings = Namespace(
            browser=user and user.browser,
            img_type=user and user.img_type,
            quality=user and user.quality,
            scale=user and user.scale,
            omit_background=user and user.omit_background,
            full_page=user and user.full_page,
            animations=user and user.animations,
        )
    if settings.img_type is None:
        settings.img_type = "png"
    if settings.img_type == "png":
        settings.quality = None
    else:
        settings.omit_background = False
    if settings.full_page is None:
        settings.full_page = True
    return settings
