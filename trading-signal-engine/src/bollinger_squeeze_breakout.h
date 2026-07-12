#pragma once

#include "strategy_interface.h"
#include "utils/circular_buffer.h"

#include <cmath>
#include <cstddef>
#include <numeric>
#include <optional>
#include <vector>

class BollingerSqueezeBreakout : public TradingStrategy {
public:
    void initialize(const nlohmann::json& params) override;
    void onCandle(const OHLCV& candle) override;
    std::optional<Signal> checkSignal() override;

private:
    // -- helpers --
    double sma(const CircularBuffer<OHLCV>& buf, size_t period) const;
    double stddev(const CircularBuffer<OHLCV>& buf, size_t period) const;
    double bandwidthAt(const CircularBuffer<OHLCV>& buf, size_t end_idx, size_t period, double mult) const;
    double currentRSI() const;

    // -- configurable params --
    size_t period_{20};
    double stddev_mult_{2.0};
    double bandwidth_threshold_{0.03};
    double volume_mult_{1.5};
    size_t squeeze_candles_{3};
    bool use_rsi_{true};
    size_t rsi_period_{14};
    double rsi_threshold_{50.0};
    size_t cooldown_candles_{4};

    // -- state --
    CircularBuffer<OHLCV> candles_{100};
    size_t since_last_signal_{0};
    std::optional<Signal> pending_;

    // RSI running state (Wilder smoothing)
    double rsi_avg_gain_{0.0};
    double rsi_avg_loss_{0.0};
    size_t rsi_count_{0};
    double prev_close_{0.0};
    bool has_prev_close_{false};
};
