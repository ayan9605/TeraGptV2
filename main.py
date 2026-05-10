# main.py
import logging
import threading
import asyncio

from pyrogram import enums, idle
from bot import app
from health import create_health_app
from config import Config
from plugins.log_channel import log_action

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
log = logging.getLogger("TeraBoxBot")

R_LOG_TXT = """<u><b>🚀 {bot_name} Restarted</b></u>

<b>⏱️ Status:</b> 🟢 <b>Online</b>
<b>📦 Version:</b> 2.1
<b>🕐 Time Zone:</b> Asia/Kolkata
<b>✅ All systems operational</b>"""

_startup_done = False
_channels_resolved = False


async def resolve_channels():
    """Resolve all configured channel peers at startup."""
    global _channels_resolved

    if _channels_resolved:
        return

    channels = {
        "LOG_CHANNEL": Config.LOG_CHANNEL,
        "ERROR_CHANNEL": Config.ERROR_CHANNEL,
        "STORAGE_CHANNEL": Config.STORAGE_CHANNEL,
        "PREMIUM_UPLOAD_CHANNEL": Config.PREMIUM_UPLOAD_CHANNEL,
    }

    log.info("🔄 Resolving configured channels...")

    for name, channel_id in channels.items():
        if not channel_id or channel_id == 0:
            log.debug("%s not configured, skipping", name)
            continue

        try:
            chat = await app.get_chat(channel_id)
            title = getattr(chat, "title", "Unknown")
            log.info("✅ %s resolved: %s (%s)", name, title, channel_id)
        except Exception as e:
            log.error("❌ %s (%s) failed to resolve: %s", name, channel_id, e)
            log.error("   Make sure bot is added as ADMIN to this channel")

    _channels_resolved = True


async def send_startup_message():
    """Send startup notification to log channel once."""
    global _startup_done

    if _startup_done:
        return

    try:
        await asyncio.sleep(2)
        await resolve_channels()

        me = await app.get_me()
        bot_username = f"@{me.username}" if getattr(me, "username", None) else "TeraBox Bot"
        msg = R_LOG_TXT.format(bot_name=bot_username)

        if Config.LOG_CHANNEL:
            await app.send_message(
                chat_id=Config.LOG_CHANNEL,
                text=msg,
                parse_mode=enums.ParseMode.HTML
            )
            log.info("✅ Restart message sent to LOG_CHANNEL")

            try:
                await log_action("main.py", f"🚀 Bot restarted successfully: {bot_username}")
            except Exception as log_err:
                log.warning("log_action failed: %s", log_err)
        else:
            log.warning("LOG_CHANNEL is not configured, skipping startup message")

        _startup_done = True

    except Exception as e:
        log.error("Could not send startup message: %s", e)


async def main():
    log.info("🔥 Pyrogram client initializing...")

    async with app:
        log.info("✅ Pyrogram client started")

        await send_startup_message()

        log.info("✅ Bot is now running and listening for updates...")
        await idle()


def run_bot():
    app.run(main())


def run_health_server():
    health_app = create_health_app()
    health_app.run(host="0.0.0.0", port=8000, debug=False, use_reloader=False)


if __name__ == "__main__":
    t = threading.Thread(target=run_health_server, daemon=True)
    t.start()
    log.info("🌐 Health server started on port 8000")

    run_bot()
