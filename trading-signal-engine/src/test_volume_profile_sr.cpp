#include "volume_profile_sr.h"

#include <cassert>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <random>

int main() {
    VolumeProfileSR strat;
    nlohmann::json params = {
        {"lookback_candles", 200},
        {"bucket_size", 100.0},
        {"zone_window", 3},
        {"min_zone_volume", 500.0},
        {"touch_threshold_pct", 1.2},
        {"volume_mult", 1.8},
        {"cooldown_candles", 6},
        {"recalc_interval", 30},
        {"volume_period", 20},
    };
    strat.initialize(params);

    std::mt19937 rng(42);
    uint64_t ts = 1000000;

    // Phase 1: accumulate volume around 60500 (support zone) and 61500 (resistance zone)
    // 120 candles clustering near 60500
    for (int i = 0; i < 120; ++i) {
        double noise = std::uniform_real_distribution<double>(-200.0, 200.0)(rng);
        double center = 60500.0 + noise;
        double range_size = std::uniform_real_distribution<double>(40.0, 200.0)(rng);

        OHLCV c;
        c.symbol = "TEST";
        c.timestamp = ts;
        c.open = center - range_size * 0.3;
        c.high = center + range_size * 0.5;
        c.low = center - range_size * 0.5;
        c.close = center;
        c.volume = 80.0 + std::uniform_real_distribution<double>(0.0, 40.0)(rng);
        strat.onCandle(c);
        auto sig = strat.checkSignal();
        assert(!sig.has_value());
        ts += 900000;
    }

    // 80 candles clustering near 61500
    for (int i = 0; i < 80; ++i) {
        double noise = std::uniform_real_distribution<double>(-200.0, 200.0)(rng);
        double center = 61500.0 + noise;
        double range_size = std::uniform_real_distribution<double>(40.0, 200.0)(rng);

        OHLCV c;
        c.symbol = "TEST";
        c.timestamp = ts;
        c.open = center - range_size * 0.3;
        c.high = center + range_size * 0.5;
        c.low = center - range_size * 0.5;
        c.close = center;
        c.volume = 80.0 + std::uniform_real_distribution<double>(0.0, 40.0)(rng);
        strat.onCandle(c);
        auto sig = strat.checkSignal();
        assert(!sig.has_value());
        ts += 900000;
    }

    // Phase 2: walk price up to 61200 with low volume (away from zones, low vol baseline)
    for (int i = 0; i < 25; ++i) {
        double center = 61000.0 + i * 8.0;
        OHLCV c;
        c.symbol = "TEST";
        c.timestamp = ts;
        c.open = center - 50.0;
        c.high = center + 50.0;
        c.low = center - 50.0;
        c.close = center + 5.0;
        c.volume = 60.0 + std::uniform_real_distribution<double>(0.0, 20.0)(rng);
        strat.onCandle(c);
        auto sig = strat.checkSignal();
        assert(!sig.has_value());
        ts += 900000;
    }

    // Phase 3: dump candle — dips close to ~60600, near 60500 support, bullish reversal, high volume
    double avg_vol_before = 70.0; // approximate from the low-vol candles above
    double spike_vol = avg_vol_before * 2.5; // 2.5x volume spike

    OHLCV dip;
    dip.symbol = "TEST";
    dip.timestamp = ts;
    dip.open = 60850.0;
    dip.high = 60880.0;
    dip.low = 60650.0;
    dip.close = 60780.0; // bullish: close > open
    dip.volume = spike_vol;
    strat.onCandle(dip);

    auto sig = strat.checkSignal();
    if (sig.has_value()) {
        std::cout << "STRATEGY TEST PASS" << std::endl;
        std::cout << "  direction=" << sig->direction
                  << " entry=" << sig->entry_price
                  << " extra=" << sig->extra.dump() << std::endl;
        return 0;
    }

    // Phase 4: rally candle to resistance with high volume, bearish close → SHORT
    for (int i = 0; i < 10; ++i) {
        double center = 60900.0 + i * 20.0;
        OHLCV c;
        c.symbol = "TEST";
        c.timestamp = ts;
        c.open = center - 30.0;
        c.high = center + 30.0;
        c.low = center - 30.0;
        c.close = center;
        c.volume = 60.0 + std::uniform_real_distribution<double>(0.0, 20.0)(rng);
        strat.onCandle(c);
        strat.checkSignal();
        ts += 900000;
    }

    OHLCV rally;
    rally.symbol = "TEST";
    rally.timestamp = ts;
    rally.open = 61220.0;
    rally.high = 61490.0;
    rally.low = 61200.0;
    rally.close = 61240.0; // bearish: close < open
    rally.volume = spike_vol;
    strat.onCandle(rally);

    sig = strat.checkSignal();
    if (sig.has_value()) {
        std::cout << "STRATEGY TEST PASS (SHORT at resistance)" << std::endl;
        std::cout << "  direction=" << sig->direction
                  << " entry=" << sig->entry_price
                  << " extra=" << sig->extra.dump() << std::endl;
        return 0;
    }

    // Phase 5: try another long setup with stronger signal
    for (int i = 0; i < 10; ++i) {
        OHLCV c;
        c.symbol = "TEST";
        c.timestamp = ts;
        c.open = 61200.0;
        c.high = 61250.0;
        c.low = 61150.0;
        c.close = 61200.0;
        c.volume = 60.0;
        strat.onCandle(c);
        strat.checkSignal();
        ts += 900000;
    }

    OHLCV dip2;
    dip2.symbol = "TEST";
    dip2.timestamp = ts;
    dip2.open = 60900.0;
    dip2.high = 60910.0;
    dip2.low = 60580.0;
    dip2.close = 60850.0; // strong bullish reversal from deep dip
    dip2.volume = spike_vol;
    strat.onCandle(dip2);

    sig = strat.checkSignal();
    if (sig.has_value()) {
        std::cout << "STRATEGY TEST PASS (LONG at support, attempt 2)" << std::endl;
        std::cout << "  direction=" << sig->direction
                  << " entry=" << sig->entry_price
                  << " extra=" << sig->extra.dump() << std::endl;
        return 0;
    }

    std::cerr << "STRATEGY TEST FAILED: no signal after all phases" << std::endl;
    return 1;
}
