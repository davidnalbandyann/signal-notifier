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
    std::optional<double> findNearestSupport(double price) const;
    std::optional<double> findNearestResistance(double price) const;
    double calcAvgVolume(size_t period) const;
    double calcSMA(size_t period) const;
    void processConfirmation(const OHLCV& candle);

    // -- configurable parameters --
    size_t lookback_candles_{300};
    double bucket_size_{100.0};
    size_t zone_window_{3};
    double min_zone_volume_{5000.0};
    double touch_threshold_pct_{0.5};
    double volume_mult_{1.5};
    size_t cooldown_candles_{6};
    size_t recalc_interval_{50};
    size_t volume_period_{20};
    double stop_loss_pct_{2.0};
    double take_profit_pct_{4.0};
    double wick_threshold_pct_{0.5};
    double body_weight_pct_{70};
    bool trend_filter_enabled_{false};
    size_t trend_period_{50};
    int confirmation_candles_{0};
    size_t max_zone_window_{50};
    std::string min_zone_volume_mode_{"absolute"};

    // -- state --
    CircularBuffer<OHLCV> candles_{600};
    CircularBuffer<double> close_prices_{600};
    std::map<int64_t, double> volume_map_;

    std::vector<double> support_levels_;
    std::vector<double> resistance_levels_;

    size_t since_last_long_{0};
    size_t since_last_short_{0};
    size_t candles_since_recalc_{0};

    struct PendingSignal {
        OHLCV trigger_candle;
        double zone_level;
        std::string zone_type;
    };
    std::optional<PendingSignal> staged_;

    std::optional<Signal> pending_;
};
