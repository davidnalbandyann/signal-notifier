#include "bollinger_squeeze_breakout.h"

#include <cassert>
#include <cmath>
#include <cstdlib>
#include <iostream>

int main() {
    BollingerSqueezeBreakout strat;
    nlohmann::json params = {
        {"period", 20},
        {"stddev_mult", 2.0},
        {"bandwidth_threshold", 0.03},
        {"volume_mult", 1.5},
        {"squeeze_candles", 3},
        {"use_rsi", true},
        {"rsi_period", 14},
        {"rsi_threshold", 50},
        {"cooldown_candles", 4},
    };
    strat.initialize(params);

    // Generate a squeeze (bandwidth shrinking) then a breakout
    // Phase 1: flat prices (narrow band) for 30 candles
    double base = 60000.0;
    uint64_t ts = 1000000;

    for (int i = 0; i < 30; ++i) {
        OHLCV c;
        c.symbol = "TEST";
        c.timestamp = ts;
        c.open = base;
        c.close = base;
        c.high = base + 100;   // very narrow range -> low bandwidth
        c.low = base - 100;
        c.volume = 100.0;
        strat.onCandle(c);
        auto sig = strat.checkSignal();
        assert(!sig.has_value());
        ts += 900000;
    }

    // Phase 2: even tighter range for 3 more candles (the squeeze_candles period)
    for (int i = 0; i < 10; ++i) {
        OHLCV c;
        c.symbol = "TEST";
        c.timestamp = ts;
        c.open = base;
        c.close = base;
        c.high = base + 10;    // extremely tight
        c.low = base - 10;
        c.volume = 100.0;
        strat.onCandle(c);
        auto sig = strat.checkSignal();
        assert(!sig.has_value());
        ts += 900000;
    }

    // Phase 3: breakout candle with volume spike
    OHLCV breakout;
    breakout.symbol = "TEST";
    breakout.timestamp = ts;
    breakout.open = base + 50;
    breakout.close = base + 500;  // big breakout above narrow band
    breakout.high = base + 550;
    breakout.low = base + 40;
    breakout.volume = 500.0;       // 5x the previous volume
    strat.onCandle(breakout);

    auto sig = strat.checkSignal();
    if (sig.has_value()) {
        std::cout << "STRATEGY TEST PASS" << std::endl;
        std::cout << "  direction=" << sig->direction
                  << " entry=" << sig->entry_price
                  << " extra=" << sig->extra.dump() << std::endl;
        return 0;
    }

    // Check if we need more cooldown candles
    std::cout << "no signal after breakout, feeding more..." << std::endl;
    for (int i = 0; i < 10; ++i) {
        OHLCV c;
        c.symbol = "TEST";
        c.timestamp = ts;
        c.open = base + 100;
        c.close = base + 200;
        c.high = base + 220;
        c.low = base + 80;
        c.volume = 200.0;
        strat.onCandle(c);
        auto sig2 = strat.checkSignal();
        ts += 900000;
    }

    // Now feed the true breakout signal
    OHLCV breakout2;
    breakout2.symbol = "TEST";
    breakout2.timestamp = ts;
    breakout2.open = base + 480;
    breakout2.close = base + 520;
    breakout2.high = base + 550;
    breakout2.low = base + 450;
    breakout2.volume = 500.0;
    strat.onCandle(breakout2);

    sig = strat.checkSignal();
    if (sig.has_value()) {
        std::cout << "STRATEGY TEST PASS" << std::endl;
        std::cout << "  direction=" << sig->direction
                  << " entry=" << sig->entry_price
                  << " extra=" << sig->extra.dump() << std::endl;
        return 0;
    }

    std::cerr << "STRATEGY TEST FAILED: no signal detected" << std::endl;
    return 1;
}
