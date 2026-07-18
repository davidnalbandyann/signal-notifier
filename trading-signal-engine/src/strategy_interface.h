#pragma once

#include "data_source_interface.h"

#include <nlohmann/json.hpp>
#include <optional>
#include <string>

struct Signal {
    std::string symbol;
    uint64_t timestamp = 0;
    std::string direction;   // "long" or "short"
    double entry_price = 0.0;
    double stop_loss = 0.0;
    double take_profit = 0.0;
    nlohmann::json extra;    // bandwidth, volume_ratio, rsi, etc.
};

class TradingStrategy {
public:
    virtual ~TradingStrategy() = default;

    virtual void onCandle(const OHLCV& candle) = 0;
    virtual std::optional<Signal> checkSignal() = 0;
    virtual void initialize(const nlohmann::json& params) = 0;
};
