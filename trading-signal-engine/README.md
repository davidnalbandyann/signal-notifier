# Trading Signal Engine (C++17)

A modular, production-ready C++ trading signal engine that streams live OHLCV data from Binance, detects Bollinger Squeeze Breakout signals, and forwards structured triggers to a Python AI analysis + notification service.

## Architecture

```
[Binance WebSocket] --closed 15m candle--> [thread-safe queue] --CV--> [main thread]
   IXWebSocket                                                        |
                                                                 onCandle() -> BollingerSqueezeBreakout
                                                                 checkSignal() -> std::optional<Signal>
                                                                 if signal -> cpr POST /trigger (sync)
                                                                               |
                                     [Python FastAPI /trigger] --+ capture screenshot
                                                                  + AI analysis (NVIDIA NIM)
                                                                  + Telegram notification
```

## Project Structure

```
trading-signal-engine/
├── CMakeLists.txt           # Build system (FetchContent for all deps)
├── config.json              # Runtime configuration
├── PLAN.md                  # Implementation plan / milestones
├── README.md                # This file
└── src/
    ├── main.cpp
    ├── data_source_interface.h    # OHLCV struct + DataSource abstract class
    ├── data_source.h / .cpp       # Factory: createDataSource()
    ├── binance_websocket_source.h / .cpp  # Binance WS client
    ├── strategy_interface.h       # Signal struct + TradingStrategy abstract class
    ├── strategy.h / .cpp          # Factory: createStrategy()
    ├── bollinger_squeeze_breakout.h / .cpp  # Strategy implementation
    ├── signal_sender.h / .cpp     # HTTP POST via cpr
    └── utils/
        ├── circular_buffer.h      # Ring buffer
        └── json_helpers.h         # Config loader
```

## Prerequisites

**macOS:**
```bash
brew install cmake openssl curl
```

**Ubuntu / Debian:**
```bash
sudo apt install cmake g++ libssl-dev libcurl4-openssl-dev
```

All C++ dependencies (nlohmann/json, spdlog, IXWebSocket, cpr, curl) are fetched automatically via CMake FetchContent. No manual library installation required beyond the system prerequisites above.

## Build & Run

```bash
# Build
cmake -S trading-signal-engine -B trading-signal-engine/build
cmake --build trading-signal-engine/build -j

# Run (from repo root or trading-signal-engine/)
./trading-signal-engine/build/trading_signal_engine [path/to/config.json]
```

### Options

- `-DBUILD_TEST_STRATEGY=ON` — builds a standalone strategy test harness (`test_strategy`)

## Configuration

See `config.json` for full example. All sections:

| Section | Key | Default | Description |
|---------|-----|---------|-------------|
| `data_source` | `type` | `"binance"` | Data source type (`binance` only for now) |
| | `symbol` | `"btcusdt"` | Trading pair (lowercase) |
| | `timeframe` | `"15m"` | Kline interval |
| `strategy` | `type` | `"bollinger_squeeze"` | Strategy type |
| | `params.period` | `20` | SMA / BB period |
| | `params.stddev_mult` | `2.0` | Standard deviation multiplier |
| | `params.bandwidth_threshold` | `0.03` | Squeeze threshold ((upper-lower)/middle) |
| | `params.volume_mult` | `1.5` | Volume spike multiplier |
| | `params.squeeze_candles` | `3` | Consecutive candles below threshold |
| | `params.use_rsi` | `true` | Enable RSI filter |
| | `params.rsi_period` | `14` | RSI calculation period |
| | `params.rsi_threshold` | `50` | Minimum RSI for long signal |
| | `params.cooldown_candles` | `4` | Min candles between signals (~1h on 15m) |
| `python_service` | `url` | — | Python `/trigger` endpoint URL |
| | `timeout_sec` | `2` | POST timeout (fire-and-forget) |
| | `auth_token` | `""` | Optional `X-Trigger-Token` shared secret |
| `logging` | `level` | `"info"` | spdlog level (trace/debug/info/warn/error) |

## Signal Logic (LONG only)

The Bollinger Squeeze Breakout triggers when ALL conditions are true:

1. **Squeeze**: Bollinger Bandwidth < `bandwidth_threshold` for `squeeze_candles` consecutive candles
2. **Breakout**: Close > Upper Bollinger Band (SMA ± 2σ)
3. **Volume**: Current volume > `volume_mult` × SMA(volume, period)
4. **RSI** (optional): RSI(Wilder, 14) > `rsi_threshold`
5. **Cooldown**: At least `cooldown_candles` since last signal

## Python `/trigger` Endpoint

The C++ engine POSTs a JSON payload to the configured Python service URL:

```json
{
  "symbol": "BTCUSDT",
  "timestamp": 1710450000,
  "direction": "long",
  "entry_price": 68350.0,
  "timeframe": "15m",
  "extra": {
    "bandwidth": 0.028,
    "volume_ratio": 1.8,
    "rsi": 56.4
  }
}
```

The Python service (`app/routes/trigger.py`) handles it by:
1. Resolving the symbol to a TradingView chart URL (DB lookup or fallback)
2. Capturing a screenshot via Playwright
3. Running AI analysis (NVIDIA NIM / MiniMax-M3)
4. Gating by `NOTIFICATION_THRESHOLD`
5. Storing in `analyses` + `notifications` DB tables
6. Sending Telegram notification with C++ signal context

**Note:** The C++ `timeout_sec` is intentionally short (2s). The Python pipeline takes ~30s+ for screenshot + AI. The POST is fire-and-forget — the C++ engine logs a timeout but the Python side completes the full pipeline.

## Adding a New Data Source

1. Create a class inheriting `DataSource` (see `data_source_interface.h`)
2. Implement `start()`, `stop()`, `getLatestCandle()`, `setOnCandle()`, `waitForCandle()`
3. Register in `createDataSource()` factory in `data_source.cpp`

## Adding a New Strategy

1. Create a class inheriting `TradingStrategy` (see `strategy_interface.h`)
2. Implement `initialize()`, `onCandle()`, `checkSignal()`
3. Register in `createStrategy()` factory in `strategy.cpp`
4. Add your params to `config.json`

## Strategy Test Harness

```bash
cmake -S trading-signal-engine -B trading-signal-engine/build \
  -DBUILD_TEST_STRATEGY=ON
cmake --build trading-signal-engine/build
./trading-signal-engine/build/test_strategy
```

Builds a standalone binary that feeds synthetic candles to the strategy and prints `STRATEGY TEST PASS` on success.
