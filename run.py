import threading
import logging
import asyncio

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_web():
    from app import app, init_db
    init_db()
    logger.info("🌐 Web server starting on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False, threaded=True)

def run_bot():
    import telegram_bot as tb
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(tb.run_bot())

def run_ff():
    import importlib.util, sys, asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    spec = importlib.util.spec_from_file_location("main_ff", "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    loop.run_until_complete(mod.StarTinG())

def main():
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    logger.info("✅ Web server thread started")

    ff_thread = threading.Thread(target=run_ff, daemon=True)
    ff_thread.start()
    logger.info("✅ Free Fire bot thread started")

    logger.info("🤖 Starting Telegram Admin Bot...")
    try:
        run_bot()
    except KeyboardInterrupt:
        logger.info("👋 Shutting down...")

if __name__ == '__main__':
    main()
