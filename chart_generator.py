"""
Chart generator.
Строит ценовой график с разметкой волн Эллиотта и уровнями Фибоначчи.
Возвращает изображение в байтах (PNG) для отправки в Telegram.
"""

import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from wave_engine import WaveCount, AnalysisResult


# Цвета
COL_BG       = "#0d1117"
COL_GRID     = "#21262d"
COL_PRICE    = "#58a6ff"
COL_WAVE_UP  = "#3fb950"
COL_WAVE_DN  = "#f85149"
COL_FIB      = "#d2a679"
COL_TEXT     = "#e6edf3"
COL_MUTED    = "#8b949e"
COL_CURRENT  = "#ffa657"

WAVE_COLORS = {
    "1": "#58a6ff", "2": "#d2a679",
    "3": "#3fb950", "4": "#d2a679",
    "5": "#58a6ff", "A": "#f85149",
    "B": "#d2a679", "C": "#f85149",
}


def generate_chart(prices: list[float], result: AnalysisResult) -> bytes:
    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor(COL_BG)
    ax.set_facecolor(COL_BG)

    n = len(prices)
    x = list(range(n))

    # Ценовая линия
    ax.plot(x, prices, color=COL_PRICE, linewidth=1.5, zorder=3, label="Цена")
    ax.fill_between(x, prices, min(prices) * 0.99, color=COL_PRICE, alpha=0.06, zorder=2)

    # Волновая разметка
    wc = result.wc
    if wc and wc.waves:
        _draw_waves(ax, wc, prices)

    # Уровни Фибоначчи
    if result.fib_levels:
        _draw_fib_levels(ax, result.fib_levels, n)

    # Текущая цена — горизонтальная линия
    ax.axhline(result.last_price, color=COL_CURRENT, linewidth=0.8,
               linestyle="--", alpha=0.7, zorder=4)

    # Оформление
    ax.set_title(
        f"{result.symbol}  |  {result.timeframe}  |  "
        f"{'📈' if (wc and wc.trend == 'UP') else '📉'} "
        f"Score: {wc.score:.0f}/100" if wc else result.symbol,
        color=COL_TEXT, fontsize=13, pad=12, fontweight="bold"
    )
    ax.set_xlabel("Бары", color=COL_MUTED, fontsize=9)
    ax.set_ylabel("Цена", color=COL_MUTED, fontsize=9)
    ax.tick_params(colors=COL_MUTED, labelsize=8)
    for spine in ax.spines.values():
        spine.set_color(COL_GRID)
    ax.grid(True, color=COL_GRID, linewidth=0.5, alpha=0.7)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(
        lambda v, _: f"{v:,.0f}" if v >= 100 else f"{v:.2f}"
    ))

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                facecolor=COL_BG, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _draw_waves(ax, wc: WaveCount, prices: list[float]):
    waves = wc.waves
    for wave in waves:
        color = WAVE_COLORS.get(wave.label, COL_TEXT)
        # Линия волны
        ax.plot(
            [wave.start_idx, wave.end_idx],
            [wave.start_price, wave.end_price],
            color=color, linewidth=2.2, zorder=5, alpha=0.9,
            linestyle="-" if wave.label in "135" else "--"
        )
        # Метка в середине волны
        mid_x = (wave.start_idx + wave.end_idx) / 2
        mid_y = (wave.start_price + wave.end_price) / 2
        offset = (max(prices) - min(prices)) * 0.04
        ax.annotate(
            f" {wave.label} ",
            xy=(mid_x, mid_y + offset),
            color=color, fontsize=11, fontweight="bold",
            ha="center", va="bottom", zorder=7,
            bbox=dict(boxstyle="round,pad=0.2", facecolor=COL_BG,
                      edgecolor=color, linewidth=0.8, alpha=0.85)
        )
        # Точки поворота
        for xi, yi in [(wave.start_idx, wave.start_price),
                       (wave.end_idx,   wave.end_price)]:
            ax.plot(xi, yi, "o", color=color, markersize=7, zorder=6,
                    markeredgecolor=COL_BG, markeredgewidth=1.5)

    # Метка текущей волны справа
    if wc.current_wave:
        ax.annotate(
            f"← Волна {wc.current_wave}",
            xy=(len(prices) - 1, prices[-1]),
            xytext=(len(prices) - 1 + len(prices) * 0.01, prices[-1]),
            color=COL_CURRENT, fontsize=10, fontweight="bold",
            va="center", zorder=8,
        )


def _draw_fib_levels(ax, fib_levels: list[dict], n_bars: int):
    for lv in fib_levels:
        hit = lv.get("hit", False)
        color = "#ffa657" if hit else COL_FIB
        alpha = 0.9 if hit else 0.45
        lw    = 1.2 if hit else 0.7
        ax.axhline(lv["price"], color=color, linewidth=lw,
                   linestyle=":", alpha=alpha, zorder=4)
        ax.text(
            n_bars * 0.01, lv["price"],
            f"  {lv['label']} {lv['price']:,.2f}",
            color=color, fontsize=7.5, alpha=alpha,
            va="center", zorder=8
        )
