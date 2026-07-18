# Build Plan: C++ Trading Signal Engine + Python `/trigger` Integration

**Branch:** `cpp-detector` (cut from `main`)
**Locked stack:** IXWebSocket (WS) · cpr (HTTP, wraps libcurl) · nlohmann/json · spdlog · CMake FetchContent · C++17 · no Boost
**Tracked plan location:** `trading-signal-engine/PLAN.md` (NOT `.opencode/plans/` — that dir is gitignored)

---

## Architecture (one diagram, do not deviate)

```
[Binance WS] --closed 15m candle--> thread-safe queue --CV--> [main thread]
   IXWebSocket thread                (mutex+condvar)            |
                                                          onCandle() -> BollingerSqueezeBreakout
                                                          checkSignal() -> std::optional<Signal>
                                                          if signal -> cpr POST /trigger (sync)
                                                                          |
                [Python FastAPI /trigger (new, public+optional shared secret)] --+
                  resolve symbol -> TradingView URL (DB or fallback construct)   |
                  BrowserService.capture -> NvidiaService.analyze                |
                  gate by NOTIFICATION_THRESHOLD                                 |
                  persist to analyses/notifications + signal_json column          |
                  TelegramService.notify (caption includes C++ signal data)      v
```

**Hard rules (do NOT reinterpret):**
- Only **closed** candles (`k.x == true`) are enqueued. Strategy NEVER sees in-progress candles.
- Strategy logic runs **only on the main thread**. The WS thread only parses + enqueues + notifies.
- Implement **LONG only** for now. `direction` is always `"long"`.
- `stop_loss` / `take_profit` are sent as `0.0` (Python/AI owns them).
- Do not refactor any working Python file beyond the exact additions listed in M6.

---

## Milestone M0 — Branch, scaffold, plan doc, .gitignore

**Goal:** empty branch with the tracked plan and a build-safe .gitignore.

**Actions:**
1. `git checkout -b cpp-detector`
2. Create `trading-signal-engine/` directory.
3. Write `trading-signal-engine/PLAN.md` = this file.
4. Append to repo `.gitignore`:
   ```
   # C++ engine
   trading-signal-engine/build/
   trading-signal-engine/_deps/
   trading-signal-engine/CMakeCache.txt
   trading-signal-engine/CMakeFiles/
   trading-signal-engine/compile_commands.json
   trading-signal-engine/*.exe
   ```
5. Commit `scaffold`.

**Verify:** `git status` shows only new files under `trading-signal-engine/` + `.gitignore`.

---

## Milestone M1 — CMake skeleton + config load + logging

**Goal:** a binary that loads `config.json` and prints it via spdlog. Proves the build + 2 of 4 deps work.

**Files:**
- `trading-signal-engine/CMakeLists.txt`
- `trading-signal-engine/config.json`
- `trading-signal-engine/src/main.cpp` (minimal)
- `trading-signal-engine/src/utils/json_helpers.h`

**CMakeLists.txt (exact):**
- `cmake_minimum_required(VERSION 3.16)`, `project(trading_signal_engine LANGUAGES CXX)`, `set(CMAKE_CXX_STANDARD 17)`, `CMAKE_CXX_STANDARD_REQUIRED ON`.
- `FetchContent` for:
  - nlohmann/json: GIT repo `https://github.com/nlohmann/json`, tag `v3.11.3`, `FetchContent_MakeAvailable(json)`.
  - spdlog: `https://github.com/gabime/spdlog`, tag `v1.13.0`, `FetchContent_MakeAvailable(spdlog)`.
- Executable `trading_signal_engine` from `src/main.cpp`, links `nlohmann_json::nlohmann_json` and `spdlog::spdlog`.
- Output dir: `set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR})`.
- (IXWebSocket + cpr added later — do NOT add now.)

**config.json (exact):**
```json
{
  "data_source": { "type": "binance", "symbol": "btcusdt", "timeframe": "15m" },
  "strategy": {
    "type": "bollinger_squeeze",
    "params": {
      "period": 20, "stddev_mult": 2.0, "bandwidth_threshold": 0.03,
      "volume_mult": 1.5, "squeeze_candles": 3,
      "use_rsi": true, "rsi_period": 14, "rsi_threshold": 50,
      "cooldown_candles": 4
    }
  },
  "python_service": { "url": "http://127.0.0.1:8000/trigger", "timeout_sec": 2, "auth_token": "" },
  "logging": { "level": "info" }
}
```

**json_helpers.h spec:** `nlohmann::json loadConfig(const std::string& path)` — reads file, throws `std::runtime_error` if missing/unparseable.

**main.cpp (M1 only):** load `config.json` via `loadConfig`, init spdlog level from `logging.level` (map "info"→`spdlog::level::info`, etc.), log each top-level section. Accept optional argv[1] as config path (default `config.json`).

**Verify:**
```
cmake -S trading-signal-engine -B trading-signal-engine/build
cmake --build trading-signal-engine/build
./trading-signal-engine/build/trading_signal_engine
```
Expected: prints the 4 config sections, exits 0.

---

## Milestone M2 — Interfaces + circular buffer (no deps beyond M1)

**Goal:** all pure-header abstractions compile.

**Files:**
- `src/data_source_interface.h` — `struct OHLCV` and `class DataSource` with the vtable from spec. Include `<functional>`, `<string>`, `<cstdint>`.
- `src/strategy_interface.h` — `struct Signal` and `class TradingStrategy` with `onCandle`, `checkSignal` (returns `std::optional<Signal>`), `initialize`. Include `<optional>`.
- `src/utils/circular_buffer.h` — template `CircularBuffer<T>` with ctor, `push`, `size`, `capacity`, `full`, `at(0=oldest)`, `latest`, `empty`. Backed by `std::vector<T>` + head + count.
- Update `main.cpp` to `#include` all three and instantiate a `CircularBuffer<OHLCV>(5)` to prove it compiles.

**Verify:** clean build succeeds. `main` still prints config + creates the buffer.

---

## Milestone M3 — BinanceWebSocketSource (add IXWebSocket)

**Goal:** connect to Binance, parse closed klines, enqueue OHLCV, wake main thread.

**Files:**
- `src/binance_websocket_source.h` / `.cpp`
- `src/data_source.h` (factory: `std::unique_ptr<DataSource> createDataSource(const json& cfg)`)
- CMake: add IXWebSocket via FetchContent — `https://github.com/machinezone/IXWebSocket`, tag `v11.4.5`. Set `USE_TLS ON` and `TLS_PROVIDER` to `openssl`. `find_package(OpenSSL REQUIRED)`, link `OpenSSL::SSL OpenSSL::Crypto`.

**BinanceWebSocketSource spec:**
- URL: `wss://stream.binance.com:9443/ws/<symbol>@kline_<timeframe>`
- Members: `ix::WebSocket ws_`, `std::thread ws_thread_`, `std::queue<OHLCV> queue_`, `std::mutex mtx_`, `std::condition_variable cv_`, `std::atomic<bool> running_{false}`, `std::function<void(const OHLCV&)> on_candle_`, OHLCV cache `latest_`.
- `start()`: `running_=true`; set URL + onMessageCallback; `ws_thread_` = `std::thread([&]{ ws_.connect(); ws_.run(); })`.
- **OnMessage callback:** Only `msg->type == Message`; parse `nlohmann::json::parse(msg->str)`. If `k.x == false` → discard. Build OHLCV from `k.s, k.t, k.o, k.h, k.l, k.c, k.v`. Lock, push, `notify_one`.
- `stop()`: `running_=false; cv_.notify_all(); ws_.stop();` join thread.
- `bool waitForCandle(OHLCV& out, int timeout_ms)` — lock, `cv_.wait_for`, pop if available, return bool.
- Factory: if `type=="binance"` return `make_unique<...>`, else throw.

**Verify:** run for ~1-2 min (point at `@kline_1m` in a throwaway config if you need fast feedback). Logs print closed candles. Ctrl-C exits cleanly.

---

## Milestone M4 — BollingerSqueezeBreakout strategy

**Goal:** correct indicators + signal logic, testable with synthetic data.

**Files:**
- `src/bollinger_squeeze_breakout.h` / `.cpp`

**Spec:**
- Members: `CircularBuffer<OHLCV> candles_{100}`, all params from `initialize`, `size_t since_last_signal_{0}`, cached `std::optional<Signal> pending_`.
- `onCandle(c)`: push; `since_last_signal_++`; update running RSI state.
- `checkSignal()`: return `pending_` then clear it.

**Formulas (implement EXACTLY):**
- `SMA(period)`: mean of last `period` closes.
- `stddev(period)`: population stddev = `sqrt(mean(x^2)-mean(x)^2)`.
- `middle=SMA`, `upper=middle+stddev_mult*stddev`, `lower=middle-stddev_mult*stddev`.
- `bandwidth=(upper-lower)/middle` (guard middle>0).
- `avg_volume=SMA(volume, period)`; `volume_ratio=current.volume/avg_volume`.
- **RSI (Wilder):** running `avg_gain, avg_loss`. First `rsi_period` deltas: simple avg. After: `avg_gain=(prev*(rsi_period-1)+gain)/rsi_period`. RS=avg_gain/avg_loss (guard loss=0→RSI=100). RSI=100-100/(1+RS).

**Signal decision (LONG only — ALL must be true):**
1. `candles_.size() >= period + squeeze_candles - 1`.
2. Squeeze: bandwidth < threshold for last `squeeze_candles` candles (current + previous 2).
3. Breakout: `current.close > upper`.
4. Volume: `volume_ratio > volume_mult`.
5. RSI (if `use_rsi`): `rsi > rsi_threshold`.
6. Cooldown: `since_last_signal_ >= cooldown_candles`.
- If all true: emit signal with `extra: {bandwidth, volume_ratio, rsi}`. Reset cooldown.

**Verify (synthetic test):** create a standalone `src/test_strategy.cpp` behind `-DBUILD_TEST_STRATEGY=ON`. Feed ~30 candles forming a squeeze→breakout. Assert `checkSignal()` returns a signal. Print "STRATEGY TEST PASS".

---

## Milestone M5 — SignalSender (add cpr) + main loop + shutdown

**Goal:** full C++ pipeline; POST happens (response from Python is optional).

**Files:**
- `src/signal_sender.h` / `.cpp`
- `src/main.cpp` (final wiring)

**CMake:** add cpr via FetchContent — `https://github.com/libcpr/cpr`, tag `1.10.5`. `find_package(CURL REQUIRED)`, link `CURL::libcurl` + `cpr::cpr`.

**SignalSender spec:**
- ctors: `SignalSender(url, timeout_sec, auth_token)`.
- `bool send(const Signal& s, const std::string& timeframe)`:
  - Build JSON: `{symbol, timestamp, direction, entry_price, timeframe, extra}`.
  - Header: `Content-Type: application/json`; `X-Trigger-Token` if `auth_token` non-empty.
  - `cpr::Post(Url{url}, Body{json.dump()}, Header{...}, Timeout{timeout_sec*1000})`.
  - Log status + body. Return `status==200`.

**main.cpp final loop:**
1. Load config.
2. Init spdlog.
3. `createDataSource`, `createStrategy`, `SignalSender`.
4. `std::atomic<bool> running{true}` + `SIGINT` handler sets false + notifies CV.
5. `source->start()`.
6. Loop: `source->waitForCandle(c, 200ms)` → `strategy->onCandle(c)` → `checkSignal()` → `sender.send()`.
7. On exit: `source->stop()`.

**Verify:** Python DOWN → no crash, logs POST failure, continues. Ctrl-C → clean shutdown.

---

## Milestone M6 — Python `/trigger` route (full integration)

**Goal:** POST from C++ → screenshot → AI → threshold gate → DB → Telegram.

**Files to create/edit:**
1. **NEW** `app/routes/trigger.py`
2. **EDIT** `app/main.py` — register router (NO auth dependency; shared-secret in-route).
3. **EDIT** `app/services/telegram.py` — optional `extra_caption` param on `notify()`.
4. **EDIT** `app/database.py` — guarded `ALTER TABLE analyses ADD COLUMN signal_json TEXT`.
5. **EDIT** `app/config/settings.py` — add `TRIGGER_TOKEN: str = ""`.
6. **EDIT** `.env.example` — add `TRIGGER_TOKEN=`.

**`trigger.py` spec:**
- `router = APIRouter(prefix="/trigger", tags=["trigger"])`.
- **Optional shared secret:** if `Settings().TRIGGER_TOKEN` set, check `X-Trigger-Token` header; else open.
- **Resolve chart:** lookup DB `charts` table for `url LIKE '%BINANCE:{symbol}%'` (symbol uppercased). Fallback: construct TradingView URL with interval mapping (`15m→15`, `1h→60`, etc.).
- **Pipeline:** `browser.capture(name, url)` → `nvidia.analyze(screenshot)` → threshold gate → persist to DB → notify Telegram with `extra_caption` from C++ signal data.
- **Mirror scheduler's DB writes** (lines 116-159 of scheduler.py) for `analyses` + `notifications` tables. Add `signal_json` column to analyses INSERT.
- Timeout: C++ may time out (2s) but Python should complete. Fire-and-forget.
- `_signal_caption(body)`: returns string like `🤖 C++ Trigger: LONG @ 68350.0 | BW 0.028 | VolR 1.8 | RSI 56.4\n`.

**telegram.py edit:** add `extra_caption: str | None = None` param to `notify()`. Prepend to caption if provided. Existing callers unchanged.

**Verify:**
```
curl -s -X POST http://127.0.0.1:8000/trigger -H 'Content-Type: application/json' \
  -d '{"symbol":"BTCUSDT","timestamp":1710450000,"direction":"long","entry_price":68350.0,"timeframe":"15m","extra":{"bandwidth":0.028,"volume_ratio":1.8,"rsi":56.4}}'
```
Expected: HTTP 200, `{"ok":true,...}`. Dashboard shows analysis row.

---

## Milestone M7 — End-to-end

**Goal:** C++ and Python running together, one real signal flows through.

**Steps:**
1. Start Python: `uvicorn app.main:app --host 0.0.0.0 --port 8000 &`
2. Start C++: `./build/trading_signal_engine`
3. To force a signal for testing (TEMPORARY throwaway `config.test.json`): `bandwidth_threshold: 10.0`, `squeeze_candles: 1`, `volume_mult: 0.0`, `use_rsi: false`, `cooldown_candles: 1`. Confirm POST round-trip. Do NOT commit test config.
4. (Optional) Lower `NOTIFICATION_THRESHOLD` in Python settings to ~1.0 for Telegram demo.

**Verify:** logs on both sides show round trip; dashboard shows triggered analysis.

---

## Milestone M8 — README + final clean build

**File:** `trading-signal-engine/README.md`

Sections: Overview, Architecture, Prerequisites (macOS: `brew install cmake openssl curl`; Ubuntu: `apt install cmake libssl-dev libcurl4-openssl-dev`), Build & Run, Config reference, Adding a data source, Adding a strategy, Python `/trigger` contract (exact JSON expected), Troubleshooting.

**Verify:** `rm -rf build && cmake -S . -B build && cmake --build build -j` from clean checkout. Binary runs. `git status` clean.

---

## Final committed tree

```
trading-signal-engine/
├── CMakeLists.txt
├── config.json
├── PLAN.md
├── README.md
└── src/
    ├── main.cpp
    ├── data_source_interface.h
    ├── data_source.h
    ├── binance_websocket_source.h / .cpp
    ├── strategy_interface.h
    ├── bollinger_squeeze_breakout.h / .cpp
    ├── signal_sender.h / .cpp
    └── utils/
        ├── circular_buffer.h
        └── json_helpers.h
```
Plus Python edits: `app/routes/trigger.py` (new), `app/main.py`, `app/services/telegram.py`, `app/database.py`, `app/config/settings.py`, `.env.example`.
