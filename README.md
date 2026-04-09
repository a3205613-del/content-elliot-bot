# Elliott Wave Telegram Bot

Telegram-бот с анализом волн Эллиотта. Данные — Yahoo Finance (акции, индексы, ETF, крипта).

## Что умеет

- Анализ любого тикера: `AAPL`, `^GSPC`, `BTC-USD`, `NVDA`...
- Таймфреймы: 1h / 4h / 1d / 1w / 1mo
- Автоматическая разметка волн 1-2-3-4-5 и A-B-C
- Проверка 3 правил Эллиотта
- Уровни Фибоначчи (коррекции + расширения)
- Целевые уровни для каждой волны
- График с визуальной разметкой (PNG)
- Кнопки выбора таймфрейма прямо в чате

---

## Шаг 1 — Создай Telegram бота

1. Открой [@BotFather](https://t.me/BotFather) в Telegram
2. Отправь `/newbot`
3. Придумай имя и username (например `ElliottWaveBot`)
4. Скопируй **BOT_TOKEN** — он выглядит как `7123456789:AAF...`

---

## Шаг 2 — Деплой на Railway (бесплатно)

### Вариант A — через GitHub (рекомендуется)

1. Создай репозиторий на [github.com](https://github.com) и загрузи все файлы:
   ```
   bot.py
   wave_engine.py
   data_fetcher.py
   chart_generator.py
   requirements.txt
   Dockerfile
   ```

2. Зайди на [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**

3. Выбери свой репозиторий

4. В разделе **Variables** добавь переменную:
   ```
   BOT_TOKEN = 7123456789:AAF...  ← твой токен от BotFather
   ```

5. Railway автоматически найдёт Dockerfile и задеплоит. Готово!

### Вариант B — через Railway CLI

```bash
npm install -g @railway/cli
railway login
railway init
railway up
railway variables set BOT_TOKEN=7123456789:AAF...
```

---

## Шаг 3 — Деплой на Render (альтернатива)

1. Зайди на [render.com](https://render.com) → **New** → **Web Service**
2. Подключи GitHub репозиторий
3. Настройки:
   - **Environment**: Docker
   - **Build Command**: *(оставь пустым)*
   - **Start Command**: `python bot.py`
4. В **Environment Variables** добавь:
   ```
   BOT_TOKEN = твой_токен
   ```
5. Deploy!

> ⚠️ На бесплатном Render сервис засыпает через 15 мин. без запросов.
> Railway держит постоянно.

---

## Локальный запуск (для тестирования)

```bash
# Установи зависимости
pip install -r requirements.txt

# Запусти
BOT_TOKEN=твой_токен python bot.py
```

---

## Команды бота

| Команда | Описание |
|---------|----------|
| `/analyze AAPL` | Анализ Apple (таймфрейм 1d по умолчанию) |
| `/analyze ^GSPC 1w` | S&P500, недельный график |
| `/analyze BTC-USD 4h` | Bitcoin, 4-часовой |
| `/symbols` | Популярные тикеры |
| `/tf` | Доступные таймфреймы |
| `/theory` | Теория волн Эллиотта |
| `/help` | Справка |

Или просто напиши тикер (`TSLA`) — бот покажет кнопки выбора таймфрейма.

---

## Структура файлов

```
bot.py              ← Telegram бот, команды, обработчики
wave_engine.py      ← Движок волнового анализа (база знаний + алгоритм)
data_fetcher.py     ← Загрузка данных с Yahoo Finance
chart_generator.py  ← Генерация графика с разметкой волн
requirements.txt    ← Зависимости Python
Dockerfile          ← Образ для деплоя
```

---

## Примеры тикеров

**Акции:** `AAPL` `TSLA` `NVDA` `MSFT` `AMZN` `META` `GOOGL`  
**Индексы:** `^GSPC` (S&P500) `^DJI` (Dow) `^IXIC` (Nasdaq)  
**ETF:** `SPY` `QQQ` `GLD` `TLT`  
**Крипта:** `BTC-USD` `ETH-USD` `SOL-USD`
