# Signal Notifier

Automated trading chart monitoring system. Captures screenshots of TradingView charts, analyzes them with NVIDIA MiniMax-M3, and sends Telegram notifications when high-quality setups are detected.

## Architecture

```
signal-notifier/
├── app/
│   ├── config/
│   │   └── settings.py          # Environment configuration (Pydantic Settings)
│   ├── models/
│   │   └── schemas.py           # Pydantic models (AnalysisResult, ChartConfig)
│   ├── routes/
│   │   ├── auth.py              # JWT login endpoint
│   │   ├── dashboard.py         # Status + scan control API
│   │   ├── charts.py            # CRUD for chart URLs
│   │   ├── analyses.py          # Analysis history + screenshots
│   │   ├── notifications.py     # Notification log
│   │   ├── settings.py          # Runtime settings editor
│   │   └── strategy.py          # Strategy prompt editor
│   ├── services/
│   │   ├── browser.py           # Playwright browser (persistent context support)
│   │   ├── gemini.py            # NVIDIA MiniMax-M3 API client
│   │   ├── scheduler.py         # APScheduler orchestration loop
│   │   └── telegram.py          # Telegram bot notifications
│   ├── auth.py                  # JWT token creation/verification
│   ├── database.py              # SQLite connection + schema
│   ├── logging_setup.py         # Structured logging (structlog)
│   ├── main.py                  # FastAPI entrypoint
│   └── state.py                 # Shared mutable state (pause/resume)
├── prompts/
│   └── strategy.md              # Trading strategy prompt (hot-reloadable)
├── scripts/
│   └── get_chat_id.py           # Helper to find your Telegram chat ID
├── urls.yaml                    # Chart URLs to monitor
├── .env.example                 # Environment variables template
├── requirements.txt
└── README.md
```

## Installation

```bash
git clone https://github.com/davidnalbandyann/signal-notifier.git
cd signal-notifier

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
python3 -m playwright install chromium

cp .env.example .env
# Edit .env with your API keys and credentials
```

## Configuration

### Environment Variables (`.env`)

| Variable | Default | Description |
|---|---|---|
| `AUTH_USERNAME` | — | Login username (required) |
| `AUTH_PASSWORD` | — | Login password (required) |
| `JWT_SECRET` | — | Secret for JWT tokens (auto-generated if empty) |
| `CHECK_INTERVAL_SECONDS` | `60` | Seconds between analysis cycles |
| `NOTIFICATION_THRESHOLD` | `8.0` | Minimum score to trigger notification (0–10) |
| `PLAYWRIGHT_WAIT_TIME` | `5` | Seconds to wait after page load before screenshot |
| `HEADLESS` | `true` | Run browser in headless mode |
| `BROWSER_VIEWPORT_WIDTH` | `1920` | Browser viewport width |
| `BROWSER_VIEWPORT_HEIGHT` | `1080` | Browser viewport height |
| `TELEGRAM_TOKEN` | — | Telegram bot token |
| `TELEGRAM_CHAT_ID` | — | Telegram chat ID to notify |
| `NVIDIA_API_KEY` | — | NVIDIA API key |
| `NVIDIA_MODEL` | `minimaxai/minimax-m3` | NVIDIA model name |
| `AI_CALL_DELAY` | `2.0` | Delay between NVIDIA API calls (rate limiting) |
| `BROWSER_USER_DATA_DIR` | — | Persistent browser session dir (set once, login persists) |
| `BROWSER_RETRY_COUNT` | `2` | Screenshot retry count |
| `BROWSER_RETRY_DELAY` | `3` | Seconds between retries |
| `URLS_FILE` | `urls.yaml` | Path to chart URLs file |

### Chart URLs (`urls.yaml`)

```yaml
charts:
  - name: "BTC/USD 15m"
    url: "https://www.tradingview.com/chart/?symbol=BINANCE:BTCUSDT&interval=15"
  - name: "ETH/USD 1h"
    url: "https://www.tradingview.com/chart/?symbol=BINANCE:ETHUSDT&interval=60"
```

### Trading Strategy Prompt (`prompts/strategy.md`)

Edit this file to modify the AI's analysis criteria. The prompt is loaded from disk every cycle — no restart needed.

## Running

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Health Check

```bash
curl http://localhost:8000/health
```

### API Docs

Swagger UI is available at `http://localhost:8000/docs` when the server is running.

## How It Works

1. **Browser** opens each chart URL, waits for it to load, takes a screenshot
2. **NVIDIA MiniMax-M3** receives the screenshot + strategy prompt, returns structured JSON with score, direction, entry/stop-loss/take-profit
3. **Scheduler** compares the score against the threshold; only notifies on setups scoring above it
4. **Telegram** sends a notification with the screenshot and analysis details
5. Repeats every `CHECK_INTERVAL_SECONDS`

Errors never stop the loop. Each chart is processed independently.

## Notification Format

```
BTC/USD 15m

Score: 8.7/10
Direction: LONG

Reason: Market structure remains bullish after liquidity sweep.

Entry: 112500
Stop Loss: 111800
Take Profit: 114900
```
