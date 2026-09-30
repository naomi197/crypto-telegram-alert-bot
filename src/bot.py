"""Telegram command handlers and application lifecycle."""
import asyncio
import logging
import math

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from .alerts import AlertStore, AlertWorker
from .config import Settings
from .market import AsyncMarketClient

logger = logging.getLogger(__name__)
HELP = ("Commands:\n/start — welcome\n/price <symbol> — current price\n"
        "/alert <symbol> <target_price> — notify once when price reaches target\n"
        "/list — your alerts\n/cancel [alert_id|all] — cancel alerts\n/help — this help")


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _services(context: ContextTypes.DEFAULT_TYPE):
    return context.application.bot_data["market"], context.application.bot_data["alerts"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text("Welcome to Crypto Alert Bot!\n\n" + HELP)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(HELP)


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    if len(context.args) != 1:
        await message.reply_text("Usage: /price BTCUSDT")
        return
    market, _ = _services(context)
    try:
        ticker = await market.get_price(context.args[0])
    except (ValueError, RuntimeError) as exc:
        await message.reply_text(f"Could not fetch price: {exc}")
    except Exception:
        logger.exception("Price lookup failed")
        await message.reply_text("Could not fetch price right now. Please try again later.")
    else:
        await message.reply_text(f"💵 {ticker.symbol}: {ticker.price:g} USDT")


async def alert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    if len(context.args) != 2:
        await message.reply_text("Usage: /alert BTCUSDT 70000")
        return
    try:
        symbol = AsyncMarketClient.normalize_symbol(context.args[0])
        target = float(context.args[1])
        if not math.isfinite(target) or target <= 0:
            raise ValueError
    except ValueError:
        await message.reply_text("Use a valid symbol and a positive target price.")
        return
    _, store = _services(context)
    created = await store.add(message.chat_id, symbol, target)
    await message.reply_text(f"✅ Alert #{created.alert_id} registered: {symbol} ≥ {target:g}")


async def list_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    _, store = _services(context)
    alerts = await store.list_for(message.chat_id)
    text = "No active alerts." if not alerts else "\n".join(
        f"#{a.alert_id} • {a.symbol} ≥ {a.target_price:g}" for a in alerts
    )
    await message.reply_text(text)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    if len(context.args) > 1:
        await message.reply_text("Usage: /cancel [alert_id|all]")
        return
    _, store = _services(context)
    if not context.args or context.args[0].lower() == "all":
        count = await store.remove_for(message.chat_id)
        await message.reply_text(f"Cancelled {count} alert(s)." if count else "No active alerts.")
        return
    try:
        alert_id = int(context.args[0])
        if alert_id <= 0:
            raise ValueError
    except ValueError:
        await message.reply_text("Usage: /cancel [alert_id|all]")
        return
    count = await store.remove_for(message.chat_id, alert_id)
    await message.reply_text("Alert cancelled." if count else "Alert not found.")


async def _post_init(application: Application) -> None:
    settings: Settings = application.bot_data["settings"]
    market = AsyncMarketClient(settings.binance_base_url, settings.request_timeout_seconds)
    await market.__aenter__()
    store = AlertStore()
    application.bot_data.update(market=market, alerts=store, stop_event=asyncio.Event())
    worker = AlertWorker(
        market, store,
        lambda chat_id, text: application.bot.send_message(chat_id=chat_id, text=text),
        settings.poll_interval_seconds,
    )
    application.bot_data["alert_task"] = asyncio.create_task(worker.run(application.bot_data["stop_event"]))


async def _post_shutdown(application: Application) -> None:
    event = application.bot_data.get("stop_event")
    task = application.bot_data.get("alert_task")
    if event is not None:
        event.set()
    if task is not None:
        await task
    market = application.bot_data.get("market")
    if market is not None:
        await market.__aexit__(None, None, None)


def build_application(settings: Settings) -> Application:
    application = Application.builder().token(settings.telegram_bot_token).post_init(_post_init).post_shutdown(_post_shutdown).build()
    application.bot_data["settings"] = settings
    for command, callback in (
        ("start", start), ("help", help_command), ("price", price),
        ("alert", alert), ("list", list_alerts), ("cancel", cancel),
    ):
        application.add_handler(CommandHandler(command, callback))
    return application


def main() -> None:
    settings = Settings.from_env()
    setup_logging(settings.log_level)
    build_application(settings).run_polling()


if __name__ == "__main__":
    main()
