"""
Elliott Wave Engine
Анализирует ценовые данные, находит волны, проверяет правила, считает цели.
"""

from dataclasses import dataclass, field
from typing import Optional
import math


# ──────────────────────────────────────────────
# ЗНАНИЯ АГЕНТА
# ──────────────────────────────────────────────

WAVE_PERSONALITIES = {
    "1": "Начало движения. Незаметная, малый объём. Часто принимают за коррекцию.",
    "2": "Коррекция волны 1. Паника, кажется что тренд не начался. Глубокая (50–61.8%).",
    "3": "⚡ Самая мощная! Высокий объём, широкое участие. Цель: 1.618× волна 1.",
    "4": "Скучная консолидация. Сложная структура. Откат ~38.2% волны 3.",
    "5": "Финальный рывок. Объём падает. Дивергенция с осцилляторами.",
    "A": "Первая коррекция. Похожа на обычный откат. Многие не замечают.",
    "B": "Ловушка! Рынок кажется восстановившимся. Не покупай.",
    "C": "Разрушительная волна. Пробивает минимум A. Равна или длиннее A.",
}

CORRECTION_PATTERNS = {
    "zigzag":   "Зигзаг (5-3-5) — резкая коррекция, самый частый паттерн.",
    "flat":     "Флэт (3-3-5) — горизонтальная, B почти достигает старта A.",
    "triangle": "Треугольник (3-3-3-3-3) — сужение перед последней волной.",
}

RULES = [
    "Волна 2 не уходит ниже начала волны 1",
    "Волна 3 никогда не является самой короткой среди 1, 3, 5",
    "Волна 4 не заходит в ценовую зону волны 1",
]

FIB_RETRACEMENTS = [0.236, 0.382, 0.500, 0.618, 0.786]
FIB_EXTENSIONS   = [1.000, 1.272, 1.618, 2.000, 2.618]


# ──────────────────────────────────────────────
# DATA STRUCTURES
# ──────────────────────────────────────────────

@dataclass
class Wave:
    label: str
    start_price: float
    end_price: float
    start_idx: int
    end_idx: int

    @property
    def length(self) -> float:
        return abs(self.end_price - self.start_price)

    @property
    def pct(self) -> float:
        return (self.end_price - self.start_price) / self.start_price * 100

    @property
    def direction(self) -> str:
        return "UP" if self.end_price > self.start_price else "DOWN"


@dataclass
class WaveCount:
    waves: list[Wave] = field(default_factory=list)
    trend: str = "UP"
    valid: bool = False
    violations: list[str] = field(default_factory=list)
    rules_ok: list[str] = field(default_factory=list)
    score: float = 0.0
    current_wave: str = "?"
    current_desc: str = ""


@dataclass
class AnalysisResult:
    symbol: str
    timeframe: str
    last_price: float
    price_change_pct: float
    wc: Optional[WaveCount]
    fib_levels: list[dict]
    targets: list[dict]
    summary: str


# ──────────────────────────────────────────────
# PIVOT DETECTION
# ──────────────────────────────────────────────

def find_pivots(prices: list[float], window: int = 3) -> list[tuple[int, float, bool]]:
    """Возвращает список (index, price, is_high)."""
    pivots = []
    n = len(prices)
    for i in range(window, n - window):
        slice_ = prices[i - window: i + window + 1]
        p = prices[i]
        if p == max(slice_):
            pivots.append((i, p, True))
        elif p == min(slice_):
            pivots.append((i, p, False))

    # Убираем подряд идущие одного типа — оставляем экстремальный
    filtered = []
    for piv in pivots:
        if filtered and filtered[-1][2] == piv[2]:
            if piv[2] and piv[1] > filtered[-1][1]:
                filtered[-1] = piv
            elif not piv[2] and piv[1] < filtered[-1][1]:
                filtered[-1] = piv
        else:
            filtered.append(piv)
    return filtered


# ──────────────────────────────────────────────
# WAVE COUNTER
# ──────────────────────────────────────────────

def build_wave_count(prices: list[float], trend: str = "UP") -> Optional[WaveCount]:
    window = max(2, len(prices) // 25)
    pivots = find_pivots(prices, window=window)

    # Набираем 6 чередующихся точек (старт + 5 поворотов)
    candidates = []
    for idx, price, is_high in pivots:
        if not candidates:
            if (trend == "UP" and not is_high) or (trend == "DOWN" and is_high):
                candidates.append((idx, price, is_high))
        else:
            last_high = candidates[-1][2]
            if is_high != last_high:
                candidates.append((idx, price, is_high))
        if len(candidates) == 6:
            break

    if len(candidates) < 6:
        return None

    labels = ["1", "2", "3", "4", "5"]
    waves = [
        Wave(
            label=labels[i],
            start_price=candidates[i][1],
            end_price=candidates[i + 1][1],
            start_idx=candidates[i][0],
            end_idx=candidates[i + 1][0],
        )
        for i in range(5)
    ]

    wc = WaveCount(waves=waves, trend=trend)
    _check_rules(wc)
    wc.score = _score(wc)
    _detect_current(wc, prices)
    return wc


def _check_rules(wc: WaveCount):
    w = wc.waves
    if len(w) < 5:
        return
    w1, w2, w3, w4, w5 = w

    # Правило 1
    if wc.trend == "UP":
        if w2.end_price < w1.start_price:
            wc.violations.append("❌ Правило 1: волна 2 ниже старта волны 1")
        else:
            wc.rules_ok.append("✅ Правило 1 соблюдено")
    else:
        if w2.end_price > w1.start_price:
            wc.violations.append("❌ Правило 1: волна 2 выше старта волны 1")
        else:
            wc.rules_ok.append("✅ Правило 1 соблюдено")

    # Правило 2
    if w3.length < w1.length and w3.length < w5.length:
        wc.violations.append("❌ Правило 2: волна 3 — самая короткая")
    else:
        wc.rules_ok.append("✅ Правило 2 соблюдено")

    # Правило 3
    if wc.trend == "UP":
        if w4.end_price < w1.end_price:
            wc.violations.append("❌ Правило 3: волна 4 зашла в зону волны 1")
        else:
            wc.rules_ok.append("✅ Правило 3 соблюдено")
    else:
        if w4.end_price > w1.end_price:
            wc.violations.append("❌ Правило 3: волна 4 зашла в зону волны 1")
        else:
            wc.rules_ok.append("✅ Правило 3 соблюдено")

    wc.valid = len(wc.violations) == 0


def _score(wc: WaveCount) -> float:
    if len(wc.waves) < 5:
        return 0.0
    w1, w2, w3, w4, w5 = wc.waves
    score = 0.0
    if w3.length >= w1.length and w3.length >= w5.length:
        score += 30
    if w1.length > 0:
        r3 = w3.length / w1.length
        if 1.4 <= r3 <= 2.8:
            score += 25
        r2 = w2.length / w1.length
        if 0.4 <= r2 <= 0.75:
            score += 20
        r5 = w5.length / w1.length
        if 0.5 <= r5 <= 1.1:
            score += 15
    if w3.length > 0:
        r4 = w4.length / w3.length
        if 0.25 <= r4 <= 0.50:
            score += 10
    return min(score, 100.0)


def _detect_current(wc: WaveCount, prices: list[float]):
    last = prices[-1]
    last_wave = wc.waves[-1]

    if len(wc.waves) == 5:
        if (wc.trend == "UP" and last < last_wave.end_price) or \
           (wc.trend == "DOWN" and last > last_wave.end_price):
            wc.current_wave = "A"
            wc.current_desc = WAVE_PERSONALITIES["A"]
        else:
            wc.current_wave = "5✓"
            wc.current_desc = "Импульс завершён. Ожидается коррекция A-B-C."
    else:
        wc.current_wave = last_wave.label
        wc.current_desc = WAVE_PERSONALITIES.get(last_wave.label, "")


# ──────────────────────────────────────────────
# FIBONACCI
# ──────────────────────────────────────────────

def calc_fib_levels(wc: WaveCount, last_price: float) -> list[dict]:
    levels = []
    if not wc.waves:
        return levels
    last_w = wc.waves[-1]
    move = last_w.end_price - last_w.start_price
    for r in FIB_RETRACEMENTS:
        price = last_w.end_price - move * r
        diff_pct = (price - last_price) / last_price * 100
        levels.append({
            "label": f"{r*100:.1f}% retrace",
            "price": round(price, 2),
            "diff_pct": round(diff_pct, 1),
            "hit": abs(last_price - price) / max(abs(move), 1) < 0.04,
        })
    return levels


def calc_targets(wc: WaveCount, last_price: float) -> list[dict]:
    targets = []
    waves = wc.waves
    direction = 1 if wc.trend == "UP" else -1

    if len(waves) >= 2:
        w1, w2 = waves[0], waves[1]
        for ext in [1.618, 2.618]:
            price = w2.end_price + direction * w1.length * ext
            diff_pct = (price - last_price) / last_price * 100
            targets.append({
                "label": f"W3 цель {ext}×W1",
                "price": round(price, 2),
                "diff_pct": round(diff_pct, 1),
            })

    if len(waves) >= 4:
        w1, w4 = waves[0], waves[3]
        for mult, lbl in [(1.0, "W5=W1"), (0.618, "W5=0.618×W1")]:
            price = w4.end_price + direction * w1.length * mult
            diff_pct = (price - last_price) / last_price * 100
            targets.append({
                "label": f"W5 цель {lbl}",
                "price": round(price, 2),
                "diff_pct": round(diff_pct, 1),
            })

    if len(waves) == 5:
        w_start = waves[0].start_price
        w_end = waves[4].end_price
        total = abs(w_end - w_start)
        for r in [0.382, 0.500, 0.618]:
            price = w_end - direction * total * r
            diff_pct = (price - last_price) / last_price * 100
            targets.append({
                "label": f"A-B-C цель {r*100:.0f}%",
                "price": round(price, 2),
                "diff_pct": round(diff_pct, 1),
            })

    return targets


# ──────────────────────────────────────────────
# MAIN ANALYSIS FUNCTION
# ──────────────────────────────────────────────

def analyze(prices: list[float], symbol: str, timeframe: str) -> AnalysisResult:
    if len(prices) < 15:
        return AnalysisResult(
            symbol=symbol, timeframe=timeframe,
            last_price=prices[-1] if prices else 0,
            price_change_pct=0, wc=None,
            fib_levels=[], targets=[],
            summary="Недостаточно данных (нужно минимум 15 баров)."
        )

    price_change = (prices[-1] - prices[-2]) / prices[-2] * 100 if len(prices) >= 2 else 0

    # Пробуем UP и DOWN, берём лучший счёт
    best: Optional[WaveCount] = None
    for trend in ["UP", "DOWN"]:
        wc = build_wave_count(prices, trend=trend)
        if wc and (best is None or wc.score > best.score):
            best = wc

    fib_levels = calc_fib_levels(best, prices[-1]) if best else []
    targets = calc_targets(best, prices[-1]) if best else []

    summary = _make_summary(symbol, timeframe, prices[-1], price_change, best)

    return AnalysisResult(
        symbol=symbol,
        timeframe=timeframe,
        last_price=prices[-1],
        price_change_pct=round(price_change, 2),
        wc=best,
        fib_levels=fib_levels,
        targets=targets,
        summary=summary,
    )


def _make_summary(symbol, tf, price, chg, wc: Optional[WaveCount]) -> str:
    lines = []
    chg_emoji = "🟢" if chg >= 0 else "🔴"
    lines.append(f"📊 *{symbol}* | {tf}")
    lines.append(f"{chg_emoji} Цена: *{price:,.2f}* ({chg:+.2f}%)\n")

    if not wc:
        lines.append("⚠️ Волновой паттерн не определён.")
        lines.append("Попробуйте другой таймфрейм или инструмент.")
        return "\n".join(lines)

    trend_emoji = "📈" if wc.trend == "UP" else "📉"
    lines.append(f"{trend_emoji} Тренд: *{'Бычий' if wc.trend == 'UP' else 'Медвежий'}*")
    lines.append(f"🎯 Уверенность: *{wc.score:.0f}/100*")
    lines.append(f"✅ Правила: *{'OK' if wc.valid else 'Нарушены'}*\n")

    lines.append("*Волновая структура:*")
    for w in wc.waves:
        arrow = "↗" if w.direction == "UP" else "↘"
        lines.append(f"  {arrow} Волна {w.label}: {w.start_price:,.2f} → {w.end_price:,.2f} ({w.pct:+.1f}%)")

    lines.append(f"\n*Текущая волна:* {wc.current_wave}")
    lines.append(f"_{wc.current_desc}_")

    if wc.violations:
        lines.append("\n*⚠️ Нарушения правил:*")
        for v in wc.violations:
            lines.append(f"  {v}")

    return "\n".join(lines)
