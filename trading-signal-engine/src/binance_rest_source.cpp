#include "binance_rest_source.h"

#include <cpr/cpr.h>
#include <nlohmann/json.hpp>
#include <spdlog/spdlog.h>

#include <algorithm>
#include <cstdint>
#include <sstream>

BinanceRestSource::BinanceRestSource(
    const std::string& symbol, const std::string& timeframe)
    : symbol_(symbol), timeframe_(timeframe) {
    // Binance REST API uses uppercase symbols
    std::string sym = symbol_;
    std::transform(sym.begin(), sym.end(), sym.begin(), ::toupper);
    std::ostringstream url;
    url << "https://api.binance.com/api/v3/klines?symbol=" << sym
        << "&interval=" << timeframe_;
    rest_url_ = url.str();
}

/*
 * Parse a single kline array from Binance REST response.
 * Response format: [open_time, open, high, low, close, volume, close_time, ...]
 * Indices:           0          1      2     3     4      5        6
 */
OHLCV BinanceRestSource::parseKline(const nlohmann::json& arr) const {
    OHLCV candle;
    candle.symbol = symbol_;
    candle.timestamp = arr[0].get<uint64_t>();
    candle.open = std::stod(arr[1].get<std::string>());
    candle.high = std::stod(arr[2].get<std::string>());
    candle.low = std::stod(arr[3].get<std::string>());
    candle.close = std::stod(arr[4].get<std::string>());
    candle.volume = std::stod(arr[5].get<std::string>());
    return candle;
}

void BinanceRestSource::fetchAndEnqueue(int limit, uint64_t end_time) {
    std::string url = rest_url_ + "&limit=" + std::to_string(limit);
    if (end_time > 0) {
        url += "&endTime=" + std::to_string(end_time);
    }

    try {
        auto r = cpr::Get(cpr::Url{url}, cpr::Timeout{10000});
        if (r.status_code != 200) {
            spdlog::error("klines API error: {} {}", r.status_code, r.text.substr(0, 200));
            return;
        }

        auto j = nlohmann::json::parse(r.text);
        if (!j.is_array()) return;

        for (auto& entry : j) {
            if (!entry.is_array() || entry.size() < 7) continue;

            uint64_t close_time = entry[6].get<uint64_t>();
            if (close_time <= last_processed_close_time_) continue;

            OHLCV candle = parseKline(entry);
            live_queue_.push(candle);
            latest_ = candle;
            latest_valid_ = true;

            // Track the close time of the last kline in each batch
            if (close_time > last_processed_close_time_) {
                last_processed_close_time_ = close_time;
            }
        }
    } catch (const std::exception& e) {
        spdlog::error("klines fetch failed: {}", e.what());
    }
}

void BinanceRestSource::start() {
    // ----- Warm-start: fetch last 150 klines -----
    spdlog::info("warming up: fetching last 150 klines from {}", rest_url_);
    try {
        std::string url = rest_url_ + "&limit=150";
        auto r = cpr::Get(cpr::Url{url}, cpr::Timeout{15000});
        if (r.status_code == 200) {
            auto j = nlohmann::json::parse(r.text);
            if (j.is_array()) {
                for (auto& entry : j) {
                    if (!entry.is_array() || entry.size() < 7) continue;
                    warm_start_.push(parseKline(entry));
                }
                if (!j.empty()) {
                    last_processed_close_time_ = j.back()[6].get<uint64_t>();
                }
                spdlog::info("warm-start: loaded {} klines", warm_start_.size());
            }
        } else {
            spdlog::error("warm-start failed: {} {}", r.status_code, r.text.substr(0, 200));
        }
    } catch (const std::exception& e) {
        spdlog::error("warm-start exception: {}", e.what());
    }

    last_poll_ = std::chrono::steady_clock::now();
    started_ = true;
    spdlog::info("data source started (REST polling every {}s)", poll_interval_sec_);
}

void BinanceRestSource::stop() {
    started_ = false;
    spdlog::info("data source stopped");
}

OHLCV BinanceRestSource::getLatestCandle(const std::string&) {
    return latest_;
}

void BinanceRestSource::setOnCandle(std::function<void(const OHLCV&)>) {
    // No-op for REST source (main loop drives the pipeline directly)
}

bool BinanceRestSource::pollCandle(OHLCV& out) {
    if (!started_) return false;

    // 1) Drain warm-start queue first
    if (!warm_start_.empty()) {
        out = warm_start_.front();
        warm_start_.pop();
        latest_ = out;
        latest_valid_ = true;
        return true;
    }

    // 2) Return any cached live candles
    if (!live_queue_.empty()) {
        out = live_queue_.front();
        live_queue_.pop();
        return true;
    }

    // 3) Check if it's time to poll the API
    auto now = std::chrono::steady_clock::now();
    auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
        now - last_poll_).count();
    if (elapsed < poll_interval_sec_) {
        return false;
    }
    last_poll_ = now;

    // Fetch limit=2: current in-progress + last closed candle
    fetchAndEnqueue(2);

    if (!live_queue_.empty()) {
        out = live_queue_.front();
        live_queue_.pop();
        return true;
    }

    return false;
}
