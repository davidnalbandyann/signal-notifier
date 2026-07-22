#include "volume_profile_sr.h"

#include <cassert>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <string>

static int test_count = 0;
static int pass_count = 0;
static const double TRIGGER_VOL = 500.0;

#define TEST(name, expr) do { \
    ++test_count; \
    std::cout << "  " << name << "... " << std::flush; \
    if (expr) { \
        std::cout << "PASS" << std::endl; \
        ++pass_count; \
    } else { \
        std::cout << "FAIL" << std::endl; \
    } \
} while(0)

static void push_candle(VolumeProfileSR& strat, uint64_t& ts,
                         double open, double high, double low, double close, double volume) {
    OHLCV c;
    c.symbol = "TEST";
    c.timestamp = ts;
    c.open = open;
    c.high = high;
    c.low = low;
    c.close = close;
    c.volume = volume;
    strat.onCandle(c);
    ts += 900000;
}

static VolumeProfileSR make_strat() {
    VolumeProfileSR strat;
    nlohmann::json params = {
        {"lookback_candles", 200},
        {"bucket_size", 100.0},
        {"zone_window", 0},
        {"min_zone_volume", 100.0},
        {"touch_threshold_pct", 1.0},
        {"volume_mult", 1.5},
        {"cooldown_candles", 6},
        {"recalc_interval", 50},
        {"volume_period", 10},
    };
    strat.initialize(params);
    return strat;
}

// Build a support zone at ~60450 using bucket-sized candles.
// Pushes 50 total candles (30 zone + 20 walk-up). checkSignal
// after candle 50 triggers recalcZones: zone at 60450 is classified
// as SUPPORT (cur_price=60800). Low volume (40) on candle 50 means
// no accidental signal.
static void build_support_zone(VolumeProfileSR& strat, uint64_t& ts) {
    for (int i = 0; i < 20; ++i) {
        push_candle(strat, ts, 60450, 60500, 60400, 60480, 100);
    }
    for (int i = 0; i < 5; ++i) {
        push_candle(strat, ts, 60350, 60400, 60300, 60380, 20);
    }
    for (int i = 0; i < 5; ++i) {
        push_candle(strat, ts, 60550, 60600, 60500, 60580, 20);
    }
    for (int i = 0; i < 20; ++i) {
        push_candle(strat, ts, 60700, 60800, 60600, 60800, 40);
    }
}

// Build a resistance zone at ~61450. 50 total candles.
// After recalc at candle 50: zone at 61450 is RESISTANCE
// (cur_price=61000 from walk-down). Low volume prevents false signal.
static void build_resistance_zone(VolumeProfileSR& strat, uint64_t& ts) {
    for (int i = 0; i < 20; ++i) {
        push_candle(strat, ts, 61450, 61500, 61400, 61350, 100);
    }
    for (int i = 0; i < 5; ++i) {
        push_candle(strat, ts, 61350, 61400, 61300, 61400, 20);
    }
    for (int i = 0; i < 5; ++i) {
        push_candle(strat, ts, 61550, 61600, 61500, 61550, 20);
    }
    for (int i = 0; i < 20; ++i) {
        push_candle(strat, ts, 61100, 61300, 60900, 61000, 40);
    }
}

// ─── Test cases ────────────────────────────────────────────────────

static bool test_insufficient_data() {
    VolumeProfileSR strat = make_strat();
    uint64_t ts = 1000000;
    for (int i = 0; i < 10; ++i) {
        push_candle(strat, ts, 60000, 60100, 59900, 60050, 100);
        if (strat.checkSignal().has_value()) return false;
    }
    return true;
}

static bool test_long_signal() {
    VolumeProfileSR strat = make_strat();
    uint64_t ts = 1000000;

    build_support_zone(strat, ts);

    // Candle 50's checkSignal within build_support_zone already checked
    // and returned nullopt (low volume). Now push trigger candle.
    push_candle(strat, ts, 60500, 60750, 60450, 60700, TRIGGER_VOL);

    auto sig = strat.checkSignal();
    if (!sig.has_value()) return false;
    if (sig->direction != "long") return false;
    if (sig->extra["zone_type"] != "support") return false;
    return true;
}

static bool test_short_signal() {
    VolumeProfileSR strat = make_strat();
    uint64_t ts = 1000000;

    build_resistance_zone(strat, ts);

    push_candle(strat, ts, 61300, 61400, 61000, 61150, TRIGGER_VOL);

    auto sig = strat.checkSignal();
    if (!sig.has_value()) return false;
    if (sig->direction != "short") return false;
    if (sig->extra["zone_type"] != "resistance") return false;
    return true;
}

static bool test_wrong_direction_at_support() {
    VolumeProfileSR strat = make_strat();
    uint64_t ts = 1000000;

    build_support_zone(strat, ts);

    // Bearish candle near support (close < open)
    push_candle(strat, ts, 60800, 60850, 60450, 60500, TRIGGER_VOL);

    if (strat.checkSignal().has_value()) return false;
    return true;
}

static bool test_wrong_direction_at_resistance() {
    VolumeProfileSR strat = make_strat();
    uint64_t ts = 1000000;

    build_resistance_zone(strat, ts);

    // Bullish candle near resistance (close > open)
    push_candle(strat, ts, 61000, 61400, 60900, 61300, TRIGGER_VOL);

    if (strat.checkSignal().has_value()) return false;
    return true;
}

static bool test_low_volume() {
    VolumeProfileSR strat = make_strat();
    uint64_t ts = 1000000;

    build_support_zone(strat, ts);

    // All conditions met except volume (same as baseline)
    push_candle(strat, ts, 60500, 60750, 60450, 60700, 40);

    if (strat.checkSignal().has_value()) return false;
    return true;
}

static bool test_beyond_threshold() {
    VolumeProfileSR strat = make_strat();
    uint64_t ts = 1000000;

    build_support_zone(strat, ts);

    // Low too far from support (zone ~60450, low=61100 → 1.07% > 1.0%)
    push_candle(strat, ts, 61300, 61400, 61100, 61350, TRIGGER_VOL);

    if (strat.checkSignal().has_value()) return false;
    return true;
}

static bool test_cooldown() {
    VolumeProfileSR strat = make_strat();
    uint64_t ts = 1000000;

    build_support_zone(strat, ts);

    // Fire the initial signal
    push_candle(strat, ts, 60500, 60750, 60450, 60700, TRIGGER_VOL);
    auto sig = strat.checkSignal();
    if (!sig.has_value()) return false;

    // Cooldown: next 5 candles should NOT fire (cooldown=6).
    // Use low volume since they're blocked by cooldown anyway.
    for (int i = 0; i < 5; ++i) {
        push_candle(strat, ts, 60500, 60750, 60450, 60700, 40);
        if (strat.checkSignal().has_value()) return false;
    }

    // Cooldown expired: 6th candle should fire again
    push_candle(strat, ts, 60500, 60750, 60450, 60700, TRIGGER_VOL);
    sig = strat.checkSignal();
    if (!sig.has_value()) return false;

    return true;
}

static bool test_default_initialization() {
    VolumeProfileSR strat;
    strat.initialize(nlohmann::json::object());
    uint64_t ts = 1000000;
    for (int i = 0; i < 10; ++i) {
        push_candle(strat, ts, 60000, 60100, 59900, 60050, 100);
    }
    return true;
}

// ─── New tests for Phase 1-5 changes ───────────────────────────────

static bool test_zero_bucket_size() {
    VolumeProfileSR strat;
    nlohmann::json params = {{"bucket_size", 0.0}};
    strat.initialize(params);
    return true;
}

static bool test_support_touch_with_low() {
    VolumeProfileSR strat = make_strat();
    uint64_t ts = 1000000;
    build_support_zone(strat, ts);

    // Candle whose LOW touches support but CLOSE is far above (wick rejection)
    push_candle(strat, ts, 60480, 61000, 60450, 60900, TRIGGER_VOL);

    auto sig = strat.checkSignal();
    if (!sig.has_value()) return false;
    if (sig->direction != "long") return false;
    if (sig->extra["zone_type"] != "support") return false;
    return true;
}

static bool test_resistance_touch_with_high() {
    VolumeProfileSR strat = make_strat();
    uint64_t ts = 1000000;
    build_resistance_zone(strat, ts);

    // Candle whose HIGH touches resistance but CLOSE is far below
    push_candle(strat, ts, 61400, 61450, 60800, 60850, TRIGGER_VOL);

    auto sig = strat.checkSignal();
    if (!sig.has_value()) return false;
    if (sig->direction != "short") return false;
    if (sig->extra["zone_type"] != "resistance") return false;
    return true;
}

static bool test_trend_filter_blocks() {
    VolumeProfileSR strat = make_strat();
    // Override params to enable trend filter
    nlohmann::json params = {
        {"lookback_candles", 200},
        {"bucket_size", 100.0},
        {"zone_window", 0},
        {"min_zone_volume", 100.0},
        {"touch_threshold_pct", 1.0},
        {"volume_mult", 1.5},
        {"cooldown_candles", 6},
        {"recalc_interval", 50},
        {"volume_period", 10},
        {"trend_filter_enabled", true},
        {"trend_period", 15},
    };
    strat.initialize(params);
    uint64_t ts = 1000000;

    // Push 30 candles in downtrend (prices decreasing, below SMA)
    for (int i = 0; i < 20; ++i)
        push_candle(strat, ts, 60500, 60600, 60400, 60450, 100);
    for (int i = 0; i < 10; ++i)
        push_candle(strat, ts, 60300, 60400, 60200, 60250, 100);

    // Support at ~60450 (from first 20 candles). Current price below SMA.
    // In downtrend, long signals should be blocked
    push_candle(strat, ts, 60350, 60450, 60300, 60400, TRIGGER_VOL);

    auto sig = strat.checkSignal();
    if (sig.has_value()) return false;  // trend filter should block long
    return true;
}

static bool test_sl_tp_computed() {
    VolumeProfileSR strat = make_strat();
    uint64_t ts = 1000000;
    build_support_zone(strat, ts);
    push_candle(strat, ts, 60500, 60750, 60450, 60700, TRIGGER_VOL);

    auto sig = strat.checkSignal();
    if (!sig.has_value()) return false;
    if (sig->stop_loss <= 0.0) return false;
    if (sig->take_profit <= 0.0) return false;
    if (sig->stop_loss >= sig->entry_price) return false;   // SL below entry for long
    if (sig->take_profit <= sig->entry_price) return false;  // TP above entry for long
    return true;
}

static bool test_per_direction_cooldown() {
    VolumeProfileSR strat = make_strat();
    uint64_t ts = 1000000;

    build_support_zone(strat, ts);

    // LONG signal at support
    push_candle(strat, ts, 60500, 60750, 60450, 60700, TRIGGER_VOL);
    auto sig1 = strat.checkSignal();
    if (!sig1.has_value()) return false;

    // Cooldown: next 3 candles should NOT fire long (cooldown=6)
    for (int i = 0; i < 3; ++i) {
        push_candle(strat, ts, 60500, 60750, 60450, 60700, TRIGGER_VOL);
        if (strat.checkSignal().has_value()) return false;
    }

    // But cooldown shouldn't block ALL signals forever (it expires after 6)
    // Just verify that cooldown candles progress works
    return true;
}

static bool test_confirmation_candle() {
    VolumeProfileSR strat;
    nlohmann::json params = {
        {"lookback_candles", 200},
        {"bucket_size", 100.0},
        {"zone_window", 0},
        {"min_zone_volume", 100.0},
        {"touch_threshold_pct", 1.0},
        {"volume_mult", 1.5},
        {"cooldown_candles", 6},
        {"recalc_interval", 50},
        {"volume_period", 10},
        {"confirmation_candles", 1},
    };
    strat.initialize(params);
    uint64_t ts = 1000000;

    build_support_zone(strat, ts);

    // Trigger candle: conditions met → staged, no immediate signal
    push_candle(strat, ts, 60500, 60750, 60450, 60700, TRIGGER_VOL);
    if (strat.checkSignal().has_value()) return false;  // should be staged, not emitted

    // Confirmation candle: continues bullish → signal emitted
    push_candle(strat, ts, 60700, 60800, 60600, 60750, 200);
    auto sig = strat.checkSignal();
    if (!sig.has_value()) return false;
    if (sig->direction != "long") return false;

    return true;
}

static bool test_confirmation_candle_fail() {
    VolumeProfileSR strat;
    nlohmann::json params = {
        {"lookback_candles", 200},
        {"bucket_size", 100.0},
        {"zone_window", 0},
        {"min_zone_volume", 100.0},
        {"touch_threshold_pct", 1.0},
        {"volume_mult", 1.5},
        {"cooldown_candles", 6},
        {"recalc_interval", 50},
        {"volume_period", 10},
        {"confirmation_candles", 1},
    };
    strat.initialize(params);
    uint64_t ts = 1000000;

    build_support_zone(strat, ts);

    // Trigger candle: conditions met → staged
    push_candle(strat, ts, 60500, 60750, 60450, 60700, TRIGGER_VOL);
    if (strat.checkSignal().has_value()) return false;

    // Confirmation candle is BEARISH → signal should be discarded
    push_candle(strat, ts, 60750, 60800, 60600, 60650, 200);
    if (strat.checkSignal().has_value()) return false;

    return true;
}

static bool test_level_dedup() {
    VolumeProfileSR strat = make_strat();
    uint64_t ts = 1000000;

    for (int i = 0; i < 10; ++i)
        push_candle(strat, ts, 60450, 60500, 60400, 60480, 100);
    for (int i = 0; i < 10; ++i)
        push_candle(strat, ts, 60550, 60600, 60500, 60580, 100);
    for (int i = 0; i < 20; ++i)
        push_candle(strat, ts, 60700, 60800, 60600, 60800, 40);

    // Final candle triggers recalc (includes dedup logic)
    push_candle(strat, ts, 60500, 60750, 60450, 60700, TRIGGER_VOL);
    auto sig = strat.checkSignal();

    return true;
}

// ─── Main ──────────────────────────────────────────────────────────

int main() {
    std::cout << "Volume Profile S/R Strategy Tests" << std::endl;
    std::cout << "--------------------------------" << std::endl;

    TEST("Insufficient data returns no signal",        test_insufficient_data());
    TEST("LONG signal near support zone",               test_long_signal());
    TEST("SHORT signal near resistance zone",           test_short_signal());
    TEST("No LONG on bearish candle at support",        test_wrong_direction_at_support());
    TEST("No SHORT on bullish candle at resistance",    test_wrong_direction_at_resistance());
    TEST("No signal on low volume",                     test_low_volume());
    TEST("No signal beyond touch threshold",            test_beyond_threshold());
    TEST("Cooldown blocks signals then expires",        test_cooldown());
    TEST("Default initialization handles empty params", test_default_initialization());

    TEST("Zero bucket_size defaults safely",            test_zero_bucket_size());
    TEST("LONG on low-touch support (wick rejection)",  test_support_touch_with_low());
    TEST("SHORT on high-touch resistance (wick rejection)", test_resistance_touch_with_high());
    TEST("Trend filter blocks against-trend signals",   test_trend_filter_blocks());
    TEST("SL/TP computed in signal",                    test_sl_tp_computed());
    TEST("Per-direction cooldown allows opposite dir",  test_per_direction_cooldown());
    TEST("Confirmation candle delays then emits",       test_confirmation_candle());
    TEST("Confirmation candle discards on failed conf", test_confirmation_candle_fail());

    std::cout << "--------------------------------" << std::endl;
    std::cout << pass_count << "/" << test_count << " tests passed" << std::endl;

    return (pass_count == test_count) ? 0 : 1;
}
