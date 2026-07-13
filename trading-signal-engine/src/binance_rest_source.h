#pragma once

#include "data_source_interface.h"

#include <chrono>
#include <nlohmann/json.hpp>
#include <queue>
#include <string>

class BinanceRestSource : public DataSource {
public:
    BinanceRestSource(const std::string& symbol, const std::string& timeframe);
    ~BinanceRestSource() override = default;

    void start() override;
    void stop() override;
    OHLCV getLatestCandle(const std::string& symbol) override;
    void setOnCandle(std::function<void(const OHLCV&)>) override;
    bool pollCandle(OHLCV& out) override;

private:
    OHLCV parseKline(const nlohmann::json& arr) const;
    void fetchAndEnqueue(int limit, uint64_t end_time = 0);

    std::string symbol_;
    std::string timeframe_;
    std::string rest_url_;
    int poll_interval_sec_{30};

    std::queue<OHLCV> warm_start_;
    std::queue<OHLCV> live_queue_;
    uint64_t last_processed_close_time_{0};
    OHLCV latest_{};
    bool latest_valid_{false};

    std::chrono::steady_clock::time_point last_poll_;
    bool started_{false};
};
