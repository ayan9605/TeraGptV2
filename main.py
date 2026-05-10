# main.py
import logging
import threading
import asyncio
from pyrogram import filters, enums
from bot import app
from health import create_health_app
from config import Config
from plugins.log_channel import log_action

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger("TeraBoxBot")

R_LOG_TXT = """<u><b>🚀 {bot_name} Restarted</b></u>

<b>⏱️ Status:</b> 🟢 <b>Online</b>
<b>📦 Version:</b> 2.1
<b>🕐 Time Zone:</b> Asia/Kolkata
<b>✅ All systems operational</b>"""

_startup_done = False
_channels_resolved = False

async def resolve_channels():
    """Resolve all configured channel peers at startup"""
    global _channels_resolved
    if _channels_resolved:
        return
    _channels_resolved = True

    channels = {
        "LOG_CHANNEL": Config.LOG_CHANNEL,
        "ERROR_CHANNEL": Config.ERROR_CHANNEL,
        "STORAGE_CHANNEL": Config.STORAGE_CHANNEL,
        "PREMIUM_UPLOAD_CHANNEL": Config.PREMIUM_UPLOAD_CHANNEL,
    }

    log.info("🔄 Resolving configured channels...")
    for name, channel_id in channels.items():
        if not channel_id or channel_id == 0:
            log.debug(f"{name} not configured, skipping")
            continue
        try:
            chat = await app.get_chat(channel_id)
            title = chat.title if hasattr(chat, 'title') else 'Unknown'
            log.info(f"✅ {name} resolved: {title} ({channel_id})")
        except Exception as e:
            log.error(f"❌ {name} ({channel_id}) failed to resolve: {e}")
            log.error(f"   Make sure bot is added as ADMIN to this channel")

async def send_startup_message():
    """Send startup notification to log channel"""
    global _startup_done
    if _startup_done:
        return
    _startup_done = True

    try:
        await asyncio.sleep(2)  # Wait for bot to be fully ready

        # Resolve all channels first
        await resolve_channels()

        me = await app.get_me()
        bot_username = "@" + me.username if getattr(me, "username", None) else "TeraBox Bot"
        msg = R_LOG_TXT.format(bot_name=bot_username)

        # Send restart message directly to log channel
        if Config.LOG_CHANNEL:
            try:
                await app.send_message(
                    chat_id=Config.LOG_CHANNEL,
                    text=msg,
                    parse_mode=enums.ParseMode.HTML
                )
                log.info("✅ Restart message sent to LOG_CHANNEL")
            except Exception as e:
                log.error(f"Failed to send restart message: {e}")
                log.error("Make sure bot is added as ADMIN to LOG_CHANNEL")
    except Exception as e:
        log.error(f"Could not send startup message: {e}")

def run_bot():
    log.info("🔥 Pyrogram client initialized & handlers loaded!")

    # Schedule startup message after bot connects
    async def startup_task():
        try:
            await app.start()
            await send_startup_message()
        except Exception as e:
            log.error(f"Error in startup: {e}")

    # Run startup in background, then start bot
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(startup_task())
    app.run()

if __name__ == "__main__":
    # Start health server (Flask) in background thread
    health_app = create_health_app()
    t = threading.Thread(target=lambda: health_app.run(host="0.0.0.0", port=8000), daemon=True)
    t.start()

    run_bot()