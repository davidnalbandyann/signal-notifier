#include "volume_profile_sr.h"

#include <spdlog/spdlog.h>

#include <algorithm>
#include <cmath>
#include <numeric>

void VolumeProfileSR::initialize(const nlohmann::json& params) {
    lookback_candles_ = params.value("lookback_candles", 300);
    bucket_size_ = params.value("bucket_size", 100.0);
    zone_window_ = params.value("zone_window", 3);
    min_zone_volume_ = params.value("min_zone_volume", 5000.0);
    touch_threshold_pct_ = params.value("touch_threshold_pct", 0.5);
    volume_mult_ = params.value("volume_mult", 1.5);
    cooldown_candles_ = params.value("cooldown_candles", 6);
    recalc_interval_ = params.value("recalc_interval", 50);
    volume_period_ = params.value("volume_period", 20);

    candles_ = CircularBuffer<OHLCV>(lookback_candles_);

    spdlog::info("volume_profile_sr initialized: lookback={} bucket={} window={}",
                 lookback_candles_, bucket_size_, zone_window_);
}

void VolumeProfileSR::onCandle(const OHLCV& candle) {
    candles_.push(candle);
    ++since_last_signal_;
    ++candles_since_recalc_;
}

std::optional<Signal> VolumeProfileSR::checkSignal() {
    if (pending_) {
        auto sig = std::move(pending_);
        pending_.reset();
        return sig;
    }

    size_t needed = std::max(volume_period_, recalc_interval_);
    if (candles_.size() < needed) {
        return std::nullopt;
    }

    if (since_last_signal_ < cooldown_candles_) {
        return std::nullopt;
    }

    if (candles_since_recalc_ >= recalc_interval_ || support_levels_.empty()) {
        recalcZones();
        candles_since_recalc_ = 0;
    }

    if (support_levels_.empty() && resistance_levels_.empty()) {
        return std::nullopt;
    }

    const OHLCV& cur = candles_.latest();
    double avg_vol = calcAvgVolume(volume_period_);
    double vol_ratio = (avg_vol > 0.0) ? cur.volume / avg_vol : 1.0;

    double sup = findNearestSupport(cur.close);
    if (sup > 0.0) {
        double dist_pct = (cur.close - sup) / sup * 100.0;
        if (dist_pct <= touch_threshold_pct_ && cur.close > cur.open && vol_ratio >= volume_mult_) {
            pending_ = Signal{};
            pending_->symbol = cur.symbol;
            pending_->timestamp = cur.timestamp;
            pending_->direction = "long";
            pending_->entry_price = cur.close;
            pending_->extra = nlohmann::json::object({
                {"zone_level", sup},
                {"zone_type", "support"},
                {"volume_ratio", vol_ratio},
                {"distance_pct", dist_pct},
            });

            since_last_signal_ = 0;
            spdlog::info("SIGNAL: {} LONG near support {} @ {} | dist={:.3f}% volR={:.2f}",
                         cur.symbol, sup, cur.close, dist_pct, vol_ratio);

            auto sig = std::move(pending_);
            pending_.reset();
            return sig;
        }
    }

    double res = findNearestResistance(cur.close);
    if (res > 0.0) {
        double dist_pct = (res - cur.close) / cur.close * 100.0;
        if (dist_pct <= touch_threshold_pct_ && cur.close < cur.open && vol_ratio >= volume_mult_) {
            pending_ = Signal{};
            pending_->symbol = cur.symbol;
            pending_->timestamp = cur.timestamp;
            pending_->direction = "short";
            pending_->entry_price = cur.close;
            pending_->extra = nlohmann::json::object({
                {"zone_level", res},
                {"zone_type", "resistance"},
                {"volume_ratio", vol_ratio},
                {"distance_pct", dist_pct},
            });

            since_last_signal_ = 0;
            spdlog::info("SIGNAL: {} SHORT near resistance {} @ {} | dist={:.3f}% volR={:.2f}",
                         cur.symbol, res, cur.close, dist_pct, vol_ratio);

            auto sig = std::move(pending_);
            pending_.reset();
            return sig;
        }
    }

    return std::nullopt;
}

void VolumeProfileSR::recalcZones() {
    volume_map_.clear();

    for (size_t i = 0; i < candles_.size(); ++i) {
        const auto& c = candles_.at(i);
        int64_t lo = static_cast<int64_t>(std::floor(c.low / bucket_size_));
        int64_t hi = static_cast<int64_t>(std::floor(c.high / bucket_size_));

        double range = c.high - c.low;
        if (range <= 0.0) range = 1.0;

        for (int64_t b = lo; b <= hi; ++b) {
            double bl = b * bucket_size_;
            double bh = bl + bucket_size_;
            double overlap = std::min(c.high, bh) - std::max(c.low, bl);
            if (overlap > 0.0) {
                volume_map_[b] += c.volume * (overlap / range);
            }
        }
    }

    if (volume_map_.empty()) return;

    int64_t min_b = volume_map_.begin()->first;
    int64_t max_b = volume_map_.rbegin()->first;
    int w = static_cast<int>(zone_window_);

    std::vector<std::pair<double, double>> smoothed;
    for (int64_t b = min_b - w; b <= max_b + w; ++b) {
        double wsum = 0.0;
        for (int64_t wb = b - w; wb <= b + w; ++wb) {
            auto it = volume_map_.find(wb);
            if (it != volume_map_.end()) {
                wsum += it->second;
            }
        }
        double price = (b + 0.5) * bucket_size_;
        smoothed.push_back({price, wsum});
    }

    support_levels_.clear();
    resistance_levels_.clear();

    double cur_price = candles_.latest().close;

    for (size_t i = 1; i + 1 < smoothed.size(); ++i) {
        double prev = smoothed[i - 1].second;
        double cur_v = smoothed[i].second;
        double next = smoothed[i + 1].second;

        if (cur_v > prev && cur_v > next && cur_v >= min_zone_volume_) {
            double level = smoothed[i].first;
            if (level < cur_price) {
                support_levels_.push_back(level);
            } else {
                resistance_levels_.push_back(level);
            }
        }
    }

    std::sort(support_levels_.begin(), support_levels_.end(), std::greater<double>());
    std::sort(resistance_levels_.begin(), resistance_levels_.end());

    spdlog::debug("volume_profile_sr recalc: {} supports, {} resistances from {} candles",
                  support_levels_.size(), resistance_levels_.size(), candles_.size());
}

double VolumeProfileSR::findNearestSupport(double price) const {
    for (double s : support_levels_) {
        if (s < price) return s;
    }
    return -1.0;
}

double VolumeProfileSR::findNearestResistance(double price) const {
    for (double r : resistance_levels_) {
        if (r > price) return r;
    }
    return -1.0;
}

double VolumeProfileSR::calcAvgVolume(size_t period) const {
    if (candles_.size() < period) return 0.0;
    double sum = 0.0;
    for (size_t i = candles_.size() - period; i < candles_.size(); ++i) {
        sum += candles_.at(i).volume;
    }
    return sum / period;
}
