"""
Data fetcher — Yahoo Finance через yfinance.
Поддерживает акции, индексы, ETF, крипту.
"""

import yfinance as yf
from datetime import datetime


TIMEFRAME_MAP = {
    "1d":  {"period": "6mo",  "interval": "1d",  "label": "Daily"},
    "4h":  {"period": "60d",  "interval": "1h",  "label": "4H (агрег.)"},
    "1h":  {"period": "7d",   "interval": "1h",  "label": "1H"},
    "1w":  {"period": "5y",   "interval": "1wk", "label": "Weekly"},
    "1mo": {"period": "10y",  "interval": "1mo", "label": "Monthly"},
}

# Популярные тикеры для подсказок
POPULAR_SYMBOLS = {
    "Индексы":  ["^GSPC (S&P500)", "^DJI (Dow)", "^IXIC (Nasdaq)", "^RUT (Russell2k)"],
    "Акции":    ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOGL", "META"],
    "ETF":      ["SPY", "QQQ", "GLD", "TLT", "VIX"],
    "Крипта":   ["BTC-USD", "ETH-USD", "SOL-USD"],
}


def fetch_prices(symbol: str, timeframe: str = "1d") -> tuple[list[float], str, str]:
    """
    Возвращает (prices, label, error_msg).
    error_msg пустой если всё ок.
    """
    tf = TIMEFRAME_MAP.get(timeframe, TIMEFRAME_MAP["1d"])

    for attempt in range(3):  # 3 попытки
        try:
            ticker = yf.Ticker(symbol.upper())
            df = ticker.history(period=tf["period"], interval=tf["interval"])

            if df is None or df.empty:
                if attempt < 2:
                    continue
                return [], "", f"Нет данных для '{symbol}'. Попробуй: SPY, QQQ, AAPL, BTC-USD"

            prices = df["Close"].dropna().tolist()

            if timeframe == "4h":
                prices = _aggregate_to_4h(prices)

            if len(prices) < 15:
                return [], "", f"Мало данных ({len(prices)} баров). Попробуй таймфрейм 1d или 1w."

            label = f"{symbol.upper()} | {tf['label']} | {len(prices)} баров"
            return prices, label, ""

        except Exception as e:
            if attempt < 2:
                continue
            return [], "", f"Ошибка загрузки '{symbol}': {str(e)[:80]}"

    return [], "", f"Не удалось загрузить данные для '{symbol}' после 3 попыток."


def get_ticker_info(symbol: str) -> dict:
    """Базовая информация о тикере."""
    try:
        t = yf.Ticker(symbol.upper())
        info = t.info
        return {
            "name":     info.get("longName") or info.get("shortName", symbol),
            "sector":   info.get("sector", "—"),
            "currency": info.get("currency", "USD"),
            "exchange": info.get("exchange", "—"),
        }
    except Exception:
        return {"name": symbol, "sector": "—", "currency": "USD", "exchange": "—"}


def _aggregate_to_4h(hourly: list[float]) -> list[float]:
    """Агрегирует часовые цены закрытия в 4-часовые (берём каждые 4)."""
    return [hourly[i] for i in range(3, len(hourly), 4)]


def format_popular_symbols() -> str:
    lines = ["*Популярные тикеры:*\n"]
    for category, symbols in POPULAR_SYMBOLS.items():
        lines.append(f"*{category}:*")
        lines.append("  " + "  |  ".join(symbols))
    return "\n".join(lines)
