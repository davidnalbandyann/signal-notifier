#include "bollinger_squeeze_breakout.h"

#include <spdlog/spdlog.h>

#include <algorithm>
#include <cmath>
#include <numeric>

void BollingerSqueezeBreakout::initialize(const nlohmann::json& params) {
    period_ = params.value("period", 20);
    stddev_mult_ = params.value("stddev_mult", 2.0);
    bandwidth_threshold_ = params.value("bandwidth_threshold", 0.03);
    volume_mult_ = params.value("volume_mult", 1.5);
    squeeze_candles_ = params.value("squeeze_candles", 3);
    use_rsi_ = params.value("use_rsi", true);
    rsi_period_ = params.value("rsi_period", 14);
    rsi_threshold_ = params.value("rsi_threshold", 50.0);
    cooldown_candles_ = params.value("cooldown_candles", 4);

    spdlog::info("strategy initialized");
}

void BollingerSqueezeBreakout::onCandle(const OHLCV& candle) {
    candles_.push(candle);
    ++since_last_signal_;

    // Update RSI running state (Wilder smoothing)
    double close = candle.close;
    if (has_prev_close_) {
        double change = close - prev_close_;
        double gain = std::max(change, 0.0);
        double loss = std::max(-change, 0.0);

        if (rsi_count_ < rsi_period_) {
            // First rsi_period deltas: simple average
            rsi_avg_gain_ = (rsi_avg_gain_ * rsi_count_ + gain) / (rsi_count_ + 1);
            rsi_avg_loss_ = (rsi_avg_loss_ * rsi_count_ + loss) / (rsi_count_ + 1);
        } else {
            // Wilder smoothing
            rsi_avg_gain_ = (rsi_avg_gain_ * (rsi_period_ - 1) + gain) / rsi_period_;
            rsi_avg_loss_ = (rsi_avg_loss_ * (rsi_period_ - 1) + loss) / rsi_period_;
        }
        ++rsi_count_;
    }
    prev_close_ = close;
    has_prev_close_ = true;
}

std::optional<Signal> BollingerSqueezeBreakout::checkSignal() {
    if (pending_) {
        auto sig = std::move(pending_);
        pending_.reset();
        return sig;
    }

    // Need enough data for BB + squeeze lookback
    size_t needed = period_ + squeeze_candles_ - 1;
    if (candles_.size() < needed) {
        return std::nullopt;
    }

    // Check cooldown
    if (since_last_signal_ < cooldown_candles_) {
        return std::nullopt;
    }

    const OHLCV& cur = candles_.latest();

    // 1) Squeeze: last N candles all have bandwidth < threshold
    for (size_t i = 0; i < squeeze_candles_; ++i) {
        double bw = bandwidthAt(candles_, candles_.size() - 1 - i, period_, stddev_mult_);
        if (bw >= bandwidth_threshold_) {
            return std::nullopt;
        }
    }

    // 2) Breakout: close > upper band
    double upper = 0.0;
    double middle = sma(candles_, period_);
    double sd = stddev(candles_, period_);
    upper = middle + stddev_mult_ * sd;

    if (cur.close <= upper) {
        return std::nullopt;
    }

    // 3) Volume spike
    double sum_vol = 0.0;
    for (size_t i = candles_.size() - period_; i < candles_.size(); ++i) {
        sum_vol += candles_.at(i).volume;
    }
    double avg_vol = sum_vol / period_;
    double vol_ratio = (avg_vol > 0.0) ? cur.volume / avg_vol : 1.0;

    if (vol_ratio <= volume_mult_) {
        return std::nullopt;
    }

    // 4) Optional RSI filter
    if (use_rsi_) {
        double rsi = currentRSI();
        if (rsi <= rsi_threshold_) {
            return std::nullopt;
        }
    }

    // All conditions met!
    double cur_bw = bandwidthAt(candles_, candles_.size() - 1, period_, stddev_mult_);

    pending_ = Signal{};
    pending_->symbol = cur.symbol;
    pending_->timestamp = cur.timestamp;
    pending_->direction = "long";
    pending_->entry_price = cur.close;
    pending_->extra = nlohmann::json::object({
        {"bandwidth", cur_bw},
        {"volume_ratio", vol_ratio},
    });
    if (use_rsi_) {
        pending_->extra["rsi"] = currentRSI();
    }

    since_last_signal_ = 0;

    spdlog::info("SIGNAL: {} LONG @ {} | BW={:.4f} VolR={:.2f}",
                  cur.symbol, cur.close, cur_bw, vol_ratio);

    auto sig = std::move(pending_);
    pending_.reset();
    return sig;
}

// === private helpers ===

double BollingerSqueezeBreakout::sma(const CircularBuffer<OHLCV>& buf, size_t period) const {
    double sum = 0.0;
    for (size_t i = buf.size() - period; i < buf.size(); ++i) {
        sum += buf.at(i).close;
    }
    return sum / period;
}

double BollingerSqueezeBreakout::stddev(const CircularBuffer<OHLCV>& buf, size_t period) const {
    double m = sma(buf, period);
    double sq_sum = 0.0;
    for (size_t i = buf.size() - period; i < buf.size(); ++i) {
        double d = buf.at(i).close - m;
        sq_sum += d * d;
    }
    return std::sqrt(sq_sum / period);
}

double BollingerSqueezeBreakout::bandwidthAt(
    const CircularBuffer<OHLCV>& buf, size_t end_idx,
    size_t period, double mult) const {
    // Compute SMA over the period ending at end_idx
    double sum = 0.0;
    for (size_t i = end_idx - period + 1; i <= end_idx; ++i) {
        sum += buf.at(i).close;
    }
    double mid = sum / period;

    double sq_sum = 0.0;
    for (size_t i = end_idx - period + 1; i <= end_idx; ++i) {
        double d = buf.at(i).close - mid;
        sq_sum += d * d;
    }
    double sd = std::sqrt(sq_sum / period);

    double upper = mid + mult * sd;
    double lower = mid - mult * sd;

    if (mid == 0.0) return 1.0;
    return (upper - lower) / mid;
}

double BollingerSqueezeBreakout::currentRSI() const {
    if (rsi_count_ < rsi_period_ || rsi_avg_loss_ == 0.0) {
        return 50.0;
    }
    double rs = rsi_avg_gain_ / rsi_avg_loss_;
    return 100.0 - 100.0 / (1.0 + rs);
}
