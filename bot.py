"""
Elliott Wave Telegram Bot
=========================
Команды:
  /start          — приветствие
  /analyze AAPL   — анализ с таймфреймом по умолчанию (1d)
  /analyze AAPL 1w — с указанием таймфрейма
  /portfolio      — сводка: Nasdaq, S&P500, Dow Jones, нефть
  /tf             — список доступных таймфреймов
  /symbols        — популярные тикеры
  /help           — справка
  /theory         — теория волн Эллиотта
"""

import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.constants import ParseMode

from data_fetcher import fetch_prices, format_popular_symbols, TIMEFRAME_MAP
from wave_engine import analyze
from chart_generator import generate_chart

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def tf_keyboard(symbol: str) -> InlineKeyboardMarkup:
    """Инлайн-кнопки выбора таймфрейма."""
    btns = [
        InlineKeyboardButton(lbl, callback_data=f"analyze:{symbol}:{tf}")
        for tf, cfg in TIMEFRAME_MAP.items()
        for lbl in [cfg["label"]]
    ]
    # По 3 кнопки в ряд
    rows = [btns[i:i+3] for i in range(0, len(btns), 3)]
    return InlineKeyboardMarkup(rows)


def targets_text(targets: list[dict]) -> str:
    if not targets:
        return ""
    lines = ["\n*🎯 Целевые уровни:*"]
    for t in targets:
        arrow = "⬆" if t["diff_pct"] > 0 else "⬇"
        lines.append(f"  {arrow} {t['label']}: `{t['price']:,.2f}` ({t['diff_pct']:+.1f}%)")
    return "\n".join(lines)


# ──────────────────────────────────────────────
# ANALYSIS CORE
# ──────────────────────────────────────────────

async def run_analysis(update: Update, symbol: str, timeframe: str):
    """Загружает данные, анализирует, отправляет график + текст."""
    chat_id = update.effective_chat.id
    msg = await update.effective_message.reply_text(
        f"⏳ Загружаю *{symbol}* [{timeframe}]...",
        parse_mode=ParseMode.MARKDOWN
    )

    prices, data_label, error = fetch_prices(symbol, timeframe)

    if error:
        await msg.edit_text(f"❌ {error}", parse_mode=ParseMode.MARKDOWN)
        return

    result = analyze(prices, symbol.upper(), TIMEFRAME_MAP[timeframe]["label"])

    # Текстовый анализ
    text = result.summary
    text += targets_text(result.targets)
    if result.wc:
        text += f"\n\n_Данные: {data_label}_"

    # График
    try:
        chart_bytes = generate_chart(prices, result)
        await msg.delete()
        await update.effective_message.reply_photo(
            photo=chart_bytes,
            caption=text,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.error(f"Chart error: {e}")
        await msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)


# ──────────────────────────────────────────────
# COMMAND HANDLERS
# ──────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 *Elliott Wave Agent*\n\n"
        "Я анализирую финансовые инструменты по теории волн Эллиотта.\n\n"
        "*Как использовать:*\n"
        "  `/analyze AAPL` — анализ Apple\n"
        "  `/analyze ^GSPC 1w` — S\\&P500, недельный\n"
        "  `/analyze BTC-USD 1d` — Bitcoin\n"
        "  `/portfolio` — Nasdaq, S&P500, Dow Jones, Нефть\n\n"
        "  `/symbols` — список популярных тикеров\n"
        "  `/tf` — доступные таймфреймы\n"
        "  `/theory` — теория волн Эллиотта\n"
        "  `/help` — справка\n"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_analyze(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if not args:
        await update.message.reply_text(
            "❗ Укажи тикер:\n`/analyze AAPL`\n`/analyze TSLA 1w`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    symbol = args[0].upper()
    timeframe = args[1].lower() if len(args) > 1 else "1d"

    if timeframe not in TIMEFRAME_MAP:
        valid = ", ".join(TIMEFRAME_MAP.keys())
        await update.message.reply_text(
            f"❗ Неизвестный таймфрейм `{timeframe}`.\nДоступные: `{valid}`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    await run_analysis(update, symbol, timeframe)


async def cmd_tf(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lines = ["*Доступные таймфреймы:*\n"]
    for key, cfg in TIMEFRAME_MAP.items():
        lines.append(f"  `{key}` — {cfg['label']}")
    lines.append("\n*Пример:* `/analyze NVDA 4h`")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_symbols(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = format_popular_symbols()
    text += "\n\n*Пример:* `/analyze ^GSPC 1w`"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "*📖 Справка Elliott Wave Agent*\n\n"
        "*Команды:*\n"
        "  `/analyze <тикер> [таймфрейм]` — анализ\n"
        "  `/portfolio [таймфрейм]` — Nasdaq, S&P500, Dow, Нефть\n"
        "  `/symbols` — популярные тикеры\n"
        "  `/tf` — таймфреймы\n"
        "  `/theory` — теория Эллиотта\n\n"
        "*Примеры тикеров:*\n"
        "  `AAPL` `TSLA` `NVDA` — акции США\n"
        "  `^GSPC` `^DJI` — индексы\n"
        "  `BTC-USD` `ETH-USD` — крипта\n"
        "  `GLD` `TLT` — ETF\n\n"
        "*Таймфреймы:*\n"
        "  `1h` `4h` `1d` `1w` `1mo`\n\n"
        "Или просто напиши тикер: `AAPL`"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ──────────────────────────────────────────────
# PORTFOLIO — Nasdaq, S&P500, Dow Jones, Oil
# ──────────────────────────────────────────────

PORTFOLIO = [
    {"symbol": "^IXIC", "name": "Nasdaq"},
    {"symbol": "^GSPC", "name": "S&P 500"},
    {"symbol": "^DJI",  "name": "Dow Jones"},
    {"symbol": "CL=F",  "name": "Нефть WTI"},
]


async def cmd_portfolio(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    timeframe = args[0].lower() if args and args[0].lower() in TIMEFRAME_MAP else "1d"
    tf_label = TIMEFRAME_MAP[timeframe]["label"]

    msg = await update.message.reply_text(
        f"⏳ Анализирую портфель [{tf_label}]...\nNasdaq • S&P500 • Dow Jones • Нефть WTI",
        parse_mode=ParseMode.MARKDOWN
    )

    results = []
    for item in PORTFOLIO:
        prices, _, error = fetch_prices(item["symbol"], timeframe)
        if error or not prices:
            results.append({"name": item["name"], "symbol": item["symbol"], "error": error or "Нет данных"})
            continue
        result = analyze(prices, item["symbol"], tf_label)
        results.append({
            "name":   item["name"],
            "symbol": item["symbol"],
            "price":  result.last_price,
            "change": result.price_change_pct,
            "wave":   result.wc.current_wave if result.wc else "?",
            "trend":  result.wc.trend if result.wc else "?",
            "score":  result.wc.score if result.wc else 0,
            "valid":  result.wc.valid if result.wc else False,
            "error":  None,
        })

    lines = [f"📋 *Портфель* | {tf_label}\n"]
    for r in results:
        if r.get("error"):
            lines.append(f"⚠️ *{r['name']}* — {r['error']}\n")
            continue
        chg_emoji   = "🟢" if r["change"] >= 0 else "🔴"
        trend_emoji = "📈" if r["trend"] == "UP" else "📉"
        rules_emoji = "✅" if r["valid"] else "⚠️"
        lines.append(
            f"{trend_emoji} *{r['name']}* (`{r['symbol']}`)\n"
            f"  {chg_emoji} {r['price']:,.2f}  ({r['change']:+.2f}%)\n"
            f"  Волна: *{r['wave']}*  |  Score: *{r['score']:.0f}/100*  {rules_emoji}\n"
        )

    # Кнопки детального анализа
    ok = [r for r in results if not r.get("error")]
    btns = [InlineKeyboardButton(f"📊 {r['name']}", callback_data=f"analyze:{r['symbol']}:{timeframe}") for r in ok]
    keyboard = InlineKeyboardMarkup([btns[:2], btns[2:]])

    lines.append("_Нажми для детального анализа ↓_")
    await msg.edit_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


async def cmd_theory(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "*📚 Теория волн Эллиотта*\n\n"
        "*Структура:* 5 импульсных волн + 3 коррекционные (A-B-C)\n\n"
        "*Волны по тренду:*\n"
        "  *1* — Начало. Незаметная, малый объём\n"
        "  *2* — Коррекция 50–61.8% волны 1\n"
        "  *3* — ⚡ Самая мощная! Цель: 1.618× волна 1\n"
        "  *4* — Боковая консолидация \\(38.2% волны 3\\)\n"
        "  *5* — Финал. Дивергенция с осцилляторами\n\n"
        "*3 железных правила:*\n"
        "  1️⃣ Волна 2 не ниже старта волны 1\n"
        "  2️⃣ Волна 3 — не самая короткая\n"
        "  3️⃣ Волна 4 не заходит в зону волны 1\n\n"
        "*Коррекция A-B-C:*\n"
        "  *A* — первая волна вниз\n"
        "  *B* — ловушка \\(ложный отскок\\)\n"
        "  *C* — основное падение, = или > A\n\n"
        "*Фибоначчи:*\n"
        "  Коррекции: 23.6% / 38.2% / 50% / 61.8%\n"
        "  Расширения: 100% / 161.8% / 261.8%"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


# ──────────────────────────────────────────────
# MESSAGE HANDLER — просто тикер в чате
# ──────────────────────────────────────────────

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    # Если похоже на тикер — показываем кнопки выбора таймфрейма
    if 1 <= len(text) <= 15 and text.replace("-", "").replace("^", "").replace(".", "").isalnum():
        await update.message.reply_text(
            f"Выбери таймфрейм для *{text}*:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=tf_keyboard(text)
        )
    else:
        await update.message.reply_text(
            "Не понял. Напиши тикер (например `AAPL`) или `/help`",
            parse_mode=ParseMode.MARKDOWN
        )


# ──────────────────────────────────────────────
# CALLBACK — кнопки таймфрейма
# ──────────────────────────────────────────────

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, symbol, timeframe = query.data.split(":")
    await run_analysis(update, symbol, timeframe)


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("analyze",   cmd_analyze))
    app.add_handler(CommandHandler("portfolio", cmd_portfolio))
    app.add_handler(CommandHandler("tf",        cmd_tf))
    app.add_handler(CommandHandler("symbols",   cmd_symbols))
    app.add_handler(CommandHandler("help",      cmd_help))
    app.add_handler(CommandHandler("theory",    cmd_theory))
    app.add_handler(CallbackQueryHandler(handle_callback, pattern=r"^analyze:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 Elliott Wave Bot запущен")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
