#pragma once

#include "strategy_interface.h"
#include "utils/circular_buffer.h"

#include <cstddef>
#include <map>
#include <optional>
#include <vector>

class VolumeProfileSR : public TradingStrategy {
public:
    void initialize(const nlohmann::json& params) override;
    void onCandle(const OHLCV& candle) override;
    std::optional<Signal> checkSignal() override;

private:
    void recalcZones();
    double findNearestSupport(double price) const;
    double findNearestResistance(double price) const;
    double calcAvgVolume(size_t period) const;

    size_t lookback_candles_{300};
    double bucket_size_{100.0};
    size_t zone_window_{3};
    double min_zone_volume_{5000.0};
    double touch_threshold_pct_{0.5};
    double volume_mult_{1.5};
    size_t cooldown_candles_{6};
    size_t recalc_interval_{50};
    size_t volume_period_{20};

    CircularBuffer<OHLCV> candles_{600};
    std::map<int64_t, double> volume_map_;

    std::vector<double> support_levels_;
    std::vector<double> resistance_levels_;

    size_t since_last_signal_{999};
    size_t candles_since_recalc_{0};
    std::optional<Signal> pending_;
};
