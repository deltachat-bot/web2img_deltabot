"""Event handlers and hooks"""
import logging
import pathlib
from argparse import Namespace
from tempfile import TemporaryDirectory
from threading import Thread
from time import sleep

from deltabot_cli import AttrDict, Bot, BotCli, EventType, const, events
from playwright.sync_api import sync_playwright

from .const import Browser
from .orm import init
from .utils import get_settings, get_url

cli = BotCli("web2img-bot")


@cli.on_init
def on_init(bot: Bot, _args: Namespace) -> None:
    if not bot.account.get_config("displayname"):
        bot.account.set_config("displayname", "Web To Image")
        status = "📸 I am a Delta Chat bot, send me any website URL to save it as image"
        bot.account.set_config("selfstatus", status)


@cli.on_start
def on_start(_bot: Bot, args: Namespace) -> None:
    """Initialize database"""
    path = pathlib.Path(args.config_dir, "sqlite.db")
    init(f"sqlite:///{path}")


@cli.on(events.RawEvent)
def log_event(event: AttrDict) -> None:
    if event.type == EventType.INFO:
        logging.info(event.msg)
    elif event.type == EventType.WARNING:
        logging.warning(event.msg)
    elif event.type == EventType.ERROR:
        logging.error(event.msg)


@cli.on(events.NewMessage(is_info=False))
def on_msg(event: AttrDict) -> None:
    """Extract the URL from the incoming message and send it as image."""
    url = get_url(event.message_snapshot.text)
    if url:
        Thread(daemon=True, target=web2img, args=(url, event.message_snapshot)).start()
        return

    chat = event.message_snapshot.chat.get_basic_snapshot()
    if chat.chat_type == const.ChatType.SINGLE:
        event.message_snapshot.chat.send_message(
            text="Send me any website URL to save it as image, for example: https://delta.chat",
            quoted_msg=event.message_snapshot.id,
        )


def web2img(url: str, snapshot: AttrDict) -> None:
    """Convert URL to image and send it in the chat it was requested."""
    try:
        _web2img(url, snapshot)
    except Exception as ex:
        logging.exception(ex)
        snapshot.chat.send_message(
            text=f"Failed to convert URL: {ex}", quoted_msg=snapshot.id
        )


def _web2img(url: str, snapshot: AttrDict) -> None:
    cfg = get_settings(snapshot.sender.id)
    with sync_playwright() as playwright:
        if cfg.browser == Browser.FIREFOX:
            browser_type = playwright.firefox
        elif cfg.browser == Browser.WEBKIT:
            browser_type = playwright.webkit
        else:
            browser_type = playwright.chromium
        browser = browser_type.launch()

        page = browser.new_page()
        page.goto(url)

        with TemporaryDirectory() as tmp_dir:
            path = pathlib.Path(tmp_dir, f"screenshot.{cfg.img_type}")
            if get_url(page.url):
                sleep(5)
                max_size = 1024**2 * 10
                size = take_screenshot(page, cfg, path)
                if size <= 0:
                    logging.warning("Invalid screenshot size: %s", size)
                    snapshot.chat.send_message(
                        text="Failed to fetch URL", quoted_msg=snapshot.id
                    )
                elif size <= max_size:
                    snapshot.chat.send_message(file=str(path), quoted_msg=snapshot.id)
                else:
                    snapshot.chat.send_message(
                        text="Ignoring URL, page too big", quoted_msg=snapshot.id
                    )
            else:
                text = f"Invalid URL redirection: {url!r} -> {page.url!r}"
                logging.warning(text)
                snapshot.chat.send_message(text=text, quoted_msg=snapshot.id)
            browser.close()


def take_screenshot(page, cfg, path) -> int:
    def _take_screenshot() -> int:
        return len(
            page.screenshot(
                path=path,
                type=cfg.img_type,
                quality=cfg.quality,
                scale=cfg.scale,
                omit_background=cfg.omit_background,
                full_page=cfg.full_page,
                animations=cfg.animations,
            )
        )

    size = _take_screenshot()

    cfg.img_type = "jpeg"
    cfg.omit_background = False
    while size > 1024**2 * 1 and cfg.quality >= 40:
        cfg.quality -= 10
        size = _take_screenshot()
    return size
