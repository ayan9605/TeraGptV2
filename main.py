# main.py
import logging
import threading
import asyncio

from pyrogram import enums, idle
from pyrogram.errors import PeerIdInvalid
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
_resolved_peers = {}


def normalize_peer(peer):
    if peer is None:
        return None

    if isinstance(peer, str):
        peer = peer.strip()
        if not peer:
            return None
        if peer.startswith("@"):
            return peer
        if peer.startswith("-100") or peer.startswith("-"):
            try:
                return int(peer)
            except ValueError:
                return peer
        return peer

    return peer


async def resolve_peer(name, peer):
    peer = normalize_peer(peer)

    if not peer:
        log.debug("%s not configured, skipping", name)
        return None

    try:
        chat = await app.get_chat(peer)
        title = getattr(chat, "title", None) or getattr(chat, "first_name", "Unknown")
        resolved_id = getattr(chat, "id", peer)
        _resolved_peers[name] = resolved_id
        log.info("✅ %s resolved: %s (%s)", name, title, resolved_id)
        return resolved_id

    except PeerIdInvalid as e:
        log.error("❌ %s (%s) failed to resolve: %s", name, peer, e)
        log.error("   Try using @username instead of numeric ID in Config")
        return None

    except Exception as e:
        log.error("❌ %s (%s) failed to resolve: %s", name, peer, e)
        return None


async def resolve_channels():
    global _channels_resolved

    if _channels_resolved:
        return

    log.info("🔄 Resolving configured channels...")

    await resolve_peer("LOG_CHANNEL", getattr(Config, "LOG_CHANNEL", None))
    await resolve_peer("ERROR_CHANNEL", getattr(Config, "ERROR_CHANNEL", None))
    await resolve_peer("STORAGE_CHANNEL", getattr(Config, "STORAGE_CHANNEL", None))
    await resolve_peer("PREMIUM_UPLOAD_CHANNEL", getattr(Config, "PREMIUM_UPLOAD_CHANNEL", None))

    _channels_resolved = True


async def send_startup_message():
    global _startup_done

    if _startup_done:
        return

    try:
        await asyncio.sleep(2)
        await resolve_channels()

        me = await app.get_me()
        bot_username = f"@{me.username}" if getattr(me, "username", None) else "TeraBox Bot"
        msg = R_LOG_TXT.format(bot_name=bot_username)

        log_channel = _resolved_peers.get("LOG_CHANNEL") or normalize_peer(getattr(Config, "LOG_CHANNEL", None))

        if log_channel:
            await app.send_message(
                chat_id=log_channel,
                text=msg,
                parse_mode=enums.ParseMode.HTML
            )
            log.info("✅ Restart message sent to LOG_CHANNEL")

            try:
                await log_action("main.py", f"🚀 Bot restarted successfully: {bot_username}")
            except Exception as log_err:
                log.warning("log_action failed: %s", log_err)
        else:
            log.warning("LOG_CHANNEL is not configured or could not be resolved")

        _startup_done = True

    except Exception as e:
        log.error("Could not send startup message: %s", e)


async def main():
    log.info("🔥 Pyrogram client initializing...")

    async with app:
        log.info("✅ Pyrogram client started")
        await send_startup_message()
        log.info("✅ Bot is now running and listening for updates")
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
