"""Event handlers and hooks"""

from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from time import sleep

from deltabot_cli import BotCli
from deltachat2 import (
    Bot,
    ChatType,
    CoreEvent,
    EventType,
    Message,
    MsgData,
    NewMsgEvent,
    events,
)
from playwright.sync_api import sync_playwright
from rich.logging import RichHandler

from ._version import __version__
from .utils import get_url, take_screenshot

cli = BotCli("web2img-bot")
cli.add_generic_option("-v", "--version", action="version", version=__version__)
cli.add_generic_option(
    "--no-time",
    help="do not display date timestamp in log messages",
    action="store_false",
)
HELP = (
    "📸 I am a Delta Chat bot, send me any website URL to save it as image."
    " Example: https://delta.chat"
)


@cli.on_init
def on_init(bot: Bot, args: Namespace) -> None:
    bot.logger.handlers = [
        RichHandler(show_path=False, omit_repeated_times=False, show_time=args.no_time)
    ]
    for accid in bot.rpc.get_all_account_ids():
        if not bot.rpc.get_config(accid, "displayname"):
            bot.rpc.set_config(accid, "displayname", "Web To Image")
            bot.rpc.set_config(accid, "selfstatus", HELP)
            bot.rpc.set_config(accid, "delete_device_after", str(60 * 60 * 24))


@cli.on(events.RawEvent)
def log_event(bot: Bot, accid: int, event: CoreEvent) -> None:
    if event.kind == EventType.INFO:
        bot.logger.debug(event.msg)
    elif event.kind == EventType.WARNING:
        bot.logger.warning(event.msg)
    elif event.kind == EventType.ERROR:
        bot.logger.error(event.msg)
    elif event.kind == EventType.MSG_DELIVERED:
        bot.rpc.delete_messages(accid, [event.msg_id])
    elif event.kind == EventType.SECUREJOIN_INVITER_PROGRESS:
        if event.progress == 1000:
            if not bot.rpc.get_contact(accid, event.contact_id).is_bot:
                bot.logger.debug("QR scanned by contact id=%s", event.contact_id)
                chatid = bot.rpc.create_chat_by_contact_id(accid, event.contact_id)
                send_help(bot, accid, chatid)


@cli.on(events.NewMessage(is_info=False))
def on_msg(bot: Bot, accid: int, event: NewMsgEvent) -> None:
    """Extract the URL from the incoming message and send it as image."""
    if bot.has_command(event.command):
        return
    msg = event.msg
    url = get_url(msg.text)
    if url:
        Thread(daemon=True, target=web2img, args=(bot, accid, msg, url)).start()
        return

    chat = bot.rpc.get_basic_chat_info(accid, msg.chat_id)
    if chat.chat_type == ChatType.SINGLE:
        send_help(bot, accid, msg.chat_id)

    bot.rpc.delete_messages(accid, [msg.id])
    bot.logger.debug(f"[chat={msg.chat_id}] Deleted message={msg.id}")


def send_help(bot: Bot, accid: int, chatid: int) -> None:
    bot.rpc.send_msg(accid, chatid, MsgData(text=HELP))


def web2img(bot: Bot, accid: int, msg: Message, url: str) -> None:
    """Convert URL to image and send it in the chat it was requested."""
    bot.rpc.send_reaction(accid, msg.id, ["⏳"])
    try:
        _web2img(bot, accid, msg, url)
    except Exception as ex:
        bot.logger.exception(ex)
        reply = MsgData(text=f"Failed to convert URL: {ex}", quoted_message_id=msg.id)
        bot.rpc.send_msg(accid, msg.chat_id, reply)
    bot.rpc.send_reaction(accid, msg.id, [])
    bot.rpc.delete_messages(accid, [msg.id])
    bot.logger.debug(f"[chat={msg.chat_id}] Deleted message={msg.id}")


def _web2img(bot: Bot, accid: int, msg: Message, url: str) -> None:
    cfg = Namespace(
        browser="firefox",
        img_type="jpeg",
        quality=90,
        scale="css",
        omit_background=False,
        full_page=True,
    )
    with sync_playwright() as playwright:
        if cfg.browser == "firefox":
            browser_type = playwright.firefox
        elif cfg.browser == "webkit":
            browser_type = playwright.webkit
        else:
            browser_type = playwright.chromium
        browser = browser_type.launch()

        page = browser.new_page()
        page.goto(url)

        reply = MsgData(quoted_message_id=msg.id)
        if get_url(page.url):
            sleep(5)
            with TemporaryDirectory() as tmp_dir:
                path = Path(tmp_dir, f"screenshot.{cfg.img_type}")
                size = take_screenshot(page, cfg, path)
                if size <= 0:
                    bot.logger.warning("Invalid screenshot size: %s", size)
                    reply.text = "Failed to fetch URL"
                elif size <= 1024**2 * 10:
                    reply.file = str(path)
                else:
                    reply.text = "Ignoring URL, page too big"
                bot.rpc.send_msg(accid, msg.chat_id, reply)
        else:
            reply.text = f"Invalid URL redirection: {url!r} -> {page.url!r}"
            bot.logger.warning(reply.text)
            bot.rpc.send_msg(accid, msg.chat_id, reply)
        browser.close()
