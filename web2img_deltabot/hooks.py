"""Event handlers and hooks"""
import asyncio
import logging
import pathlib
from argparse import Namespace

import aiofiles
from playwright.async_api import async_playwright
from simplebot_aio import AttrDict, Bot, BotCli, EventType, const, events

from .const import Browser
from .orm import init
from .utils import get_settings, get_url

cli = BotCli()


@cli.on(events.RawEvent)
async def log_event(event: AttrDict) -> None:
    if event.type == EventType.INFO:
        logging.info(event.msg)
    elif event.type == EventType.WARNING:
        logging.warning(event.msg)
    elif event.type == EventType.ERROR:
        logging.error(event.msg)


@cli.on(events.NewMessage(func=lambda ev: not ev.command))
async def on_msg(event: AttrDict) -> None:
    """Extract the URL from the incoming message and send it as image."""
    snapshot = await event.chat.get_basic_snapshot()
    url = get_url(event.text)
    if url:
        asyncio.create_task(web2img(url, event))
    elif snapshot.chat_type == const.ChatType.SINGLE:
        await event.chat.send_message(
            text="Send me any website URL to save it as image, for example: https://delta.chat",
            quoted_msg=event.id,
        )


@cli.on_start
async def on_start(bot: Bot, args: Namespace) -> None:
    """Initialize database"""
    path = pathlib.Path(args.config_dir, "sqlite.db")
    await init(f"sqlite+aiosqlite:///{path}")


async def web2img(url: str, event: AttrDict) -> None:
    """Convert URL to image and send it in the chat it was requested."""
    try:
        await _web2img(url, event)
    except Exception as ex:
        logging.exception(ex)
        await event.chat.send_message(
            text=f"Failed to convert URL: {ex}", quoted_msg=event.id
        )


async def _web2img(url: str, event: AttrDict) -> None:
    cfg = await get_settings(event.sender.id)
    async with async_playwright() as playwright:
        if cfg.browser == Browser.FIREFOX:
            browser_type = playwright.firefox
        elif cfg.browser == Browser.WEBKIT:
            browser_type = playwright.webkit
        else:
            browser_type = playwright.chromium
        browser = await browser_type.launch()

        page = await browser.new_page()
        await page.goto(url)

        async with aiofiles.tempfile.TemporaryDirectory() as tmp_dir:
            path = pathlib.Path(tmp_dir, f"screenshot.{cfg.img_type or 'png'}")
            if get_url(page.url):
                await page.screenshot(
                    path=path,
                    quality=None if cfg.img_type == "png" else cfg.quality,
                    scale=cfg.scale,
                    omit_background=cfg.omit_background,
                    full_page=cfg.full_page,
                    animations=cfg.animations,
                )
                await event.chat.send_message(file=str(path), quoted_msg=event.id)
            else:
                text = f"Invalid URL redirection: {url!r} -> {page.url!r}"
                logging.warning(text)
                await event.chat.send_message(text=text, quoted_msg=event.id)
            await browser.close()