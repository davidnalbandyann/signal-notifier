#pragma once

#include <cstdint>
#include <functional>
#include <string>

struct OHLCV {
    std::string symbol;
    uint64_t timestamp; // ms epoch
    double open = 0.0;
    double high = 0.0;
    double low = 0.0;
    double close = 0.0;
    double volume = 0.0;
};

class DataSource {
public:
    virtual ~DataSource() = default;

    virtual void start() = 0;
    virtual void stop() = 0;
    virtual OHLCV getLatestCandle(const std::string& symbol) = 0;
    virtual void setOnCandle(std::function<void(const OHLCV&)>) = 0;
    virtual bool pollCandle(OHLCV& out) = 0;
};
