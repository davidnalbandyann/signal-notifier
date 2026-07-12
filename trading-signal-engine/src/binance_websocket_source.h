#pragma once

#include "data_source_interface.h"

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <functional>
#include <mutex>
#include <queue>
#include <string>

#include <ixwebsocket/IXWebSocket.h>

class BinanceWebSocketSource : public DataSource {
public:
    BinanceWebSocketSource(const std::string& symbol, const std::string& timeframe);
    ~BinanceWebSocketSource() override;

    void start() override;
    void stop() override;
    OHLCV getLatestCandle(const std::string& symbol) override;
    void setOnCandle(std::function<void(const OHLCV&)>) override;

    bool waitForCandle(OHLCV& out, int timeout_ms);

private:
    void onMessage(const std::string& raw);

    std::string stream_url_;
    ix::WebSocket ws_;
    std::queue<OHLCV> queue_;
    std::mutex mtx_;
    std::condition_variable cv_;
    std::atomic<bool> running_{false};
    std::function<void(const OHLCV&)> on_candle_;
    OHLCV latest_{};
    bool latest_valid_{false};
};
