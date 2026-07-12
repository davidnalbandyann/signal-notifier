#include "binance_websocket_source.h"

#include <nlohmann/json.hpp>
#include <spdlog/spdlog.h>

#include <sstream>

BinanceWebSocketSource::BinanceWebSocketSource(
    const std::string& symbol, const std::string& timeframe) {
    // Binance WS endpoint uses lowercase symbol
    std::ostringstream url;
    url << "wss://stream.binance.com:9443/ws/" << symbol << "@kline_" << timeframe;
    stream_url_ = url.str();
}

BinanceWebSocketSource::~BinanceWebSocketSource() {
    stop();
}

void BinanceWebSocketSource::start() {
    running_ = true;
    ws_.setUrl(stream_url_);

    ws_.setOnMessageCallback([this](const ix::WebSocketMessagePtr& msg) {
        if (msg->type == ix::WebSocketMessageType::Open) {
            spdlog::info("ws connected: {}", stream_url_);
        } else if (msg->type == ix::WebSocketMessageType::Close) {
            spdlog::info("ws closed: code={} reason={}", msg->closeInfo.code, msg->closeInfo.reason);
        } else if (msg->type == ix::WebSocketMessageType::Error) {
            spdlog::error("ws error: {}", msg->errorInfo.reason);
        } else if (msg->type == ix::WebSocketMessageType::Message) {
            onMessage(msg->str);
        }
    });

    ws_.start();
    spdlog::info("data source started: {}", stream_url_);
}

void BinanceWebSocketSource::stop() {
    running_ = false;
    ws_.stop();
    cv_.notify_all();
    spdlog::info("data source stopped");
}

/*
 * Parse a Binance kline WebSocket message.
 * Expected payload structure:
 * {
 *   "s": "BTCUSDT",
 *   "k": {
 *     "t": <start_time_ms>,
 *     "o": <open>,
 *     "h": <high>,
 *     "l": <low>,
 *     "c": <close>,
 *     "v": <volume>,
 *     "x": <bool: is_closed>
 *   }
 * }
 *
 * Only candles with k.x == true (closed) are enqueued.
 */
void BinanceWebSocketSource::onMessage(const std::string& raw) {
    auto j = nlohmann::json::parse(raw, nullptr, false);
    if (!j.is_object() || !j.contains("k")) {
        return;
    }

    auto& k = j["k"];
    if (!k.contains("x")) return;

    // Only process closed 15m candles
    if (!k["x"].get<bool>()) return;

    try {
        OHLCV candle;
        candle.symbol = j.value("s", std::string());
        candle.timestamp = k["t"].get<uint64_t>();
        candle.open = std::stod(k["o"].get<std::string>());
        candle.high = std::stod(k["h"].get<std::string>());
        candle.low = std::stod(k["l"].get<std::string>());
        candle.close = std::stod(k["c"].get<std::string>());
        candle.volume = std::stod(k["v"].get<std::string>());

        {
            std::lock_guard<std::mutex> lock(mtx_);
            queue_.push(candle);
            latest_ = candle;
            latest_valid_ = true;
        }
        cv_.notify_one();

        spdlog::info("candle: {} close={} ts={} vol={}",
                      candle.symbol, candle.close, candle.timestamp, candle.volume);

        if (on_candle_) {
            on_candle_(candle);
        }
    } catch (const std::exception& e) {
        spdlog::error("failed to parse kline: {}", e.what());
    }
}

OHLCV BinanceWebSocketSource::getLatestCandle(const std::string& /*symbol*/) {
    std::lock_guard<std::mutex> lock(mtx_);
    return latest_;
}

void BinanceWebSocketSource::setOnCandle(std::function<void(const OHLCV&)> cb) {
    on_candle_ = std::move(cb);
}

bool BinanceWebSocketSource::waitForCandle(OHLCV& out, int timeout_ms) {
    std::unique_lock<std::mutex> lock(mtx_);
    if (!queue_.empty()) {
        out = queue_.front();
        queue_.pop();
        return true;
    }
    cv_.wait_for(lock, std::chrono::milliseconds(timeout_ms));
    if (!queue_.empty()) {
        out = queue_.front();
        queue_.pop();
        return true;
    }
    return false;
}
