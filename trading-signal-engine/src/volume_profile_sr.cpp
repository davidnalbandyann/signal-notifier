#include "volume_profile_sr.h"

#include <spdlog/spdlog.h>

#include <algorithm>
#include <cmath>
#include <numeric>
#include <unordered_set>

void VolumeProfileSR::initialize(const nlohmann::json& params) {
    lookback_candles_    = params.value("lookback_candles", 300);
    bucket_size_         = params.value("bucket_size", 100.0);
    zone_window_         = params.value("zone_window", 3);
    min_zone_volume_     = params.value("min_zone_volume", 5000.0);
    touch_threshold_pct_ = params.value("touch_threshold_pct", 0.5);
    volume_mult_         = params.value("volume_mult", 1.5);
    cooldown_candles_    = params.value("cooldown_candles", 6);
    recalc_interval_     = params.value("recalc_interval", 50);
    volume_period_       = params.value("volume_period", 20);
    stop_loss_pct_       = params.value("stop_loss_pct", 2.0);
    take_profit_pct_     = params.value("take_profit_pct", 4.0);
    wick_threshold_pct_  = params.value("wick_threshold_pct", 0.5);
    body_weight_pct_     = params.value("body_weight_pct", 70);
    trend_filter_enabled_= params.value("trend_filter_enabled", false);
    trend_period_        = params.value("trend_period", 50);
    confirmation_candles_= params.value("confirmation_candles", 0);
    max_zone_window_     = params.value("max_zone_window", 50);
    min_zone_volume_mode_= params.value("min_zone_volume_mode", std::string("absolute"));

    if (bucket_size_ <= 0.0) bucket_size_ = 100.0;
    if (zone_window_ > max_zone_window_) zone_window_ = max_zone_window_;

    candles_ = CircularBuffer<OHLCV>(lookback_candles_);
    close_prices_ = CircularBuffer<double>(lookback_candles_);

    spdlog::info("volume_profile_sr initialized: lookback={} bucket={} window={}",
                 lookback_candles_, bucket_size_, zone_window_);
}

void VolumeProfileSR::onCandle(const OHLCV& candle) {
    candles_.push(candle);
    close_prices_.push(candle.close);

    if (confirmation_candles_ > 0 && staged_) {
        processConfirmation(candle);
    }

    ++since_last_long_;
    ++since_last_short_;
    ++candles_since_recalc_;
}

void VolumeProfileSR::processConfirmation(const OHLCV& candle) {
    if (!staged_) return;

    bool confirmed = false;
    if (staged_->zone_type == "support") {
        confirmed = candle.close > candle.open && candle.low <= staged_->zone_level + staged_->zone_level * wick_threshold_pct_ / 100.0;
    } else {
        confirmed = candle.close < candle.open && candle.high >= staged_->zone_level - staged_->zone_level * wick_threshold_pct_ / 100.0;
    }

    if (confirmed) {
        const auto& tc = staged_->trigger_candle;
        Signal sig;
        sig.symbol = tc.symbol;
        sig.timestamp = tc.timestamp;
        sig.direction = (staged_->zone_type == "support") ? "long" : "short";
        sig.entry_price = tc.close;
        sig.stop_loss = (staged_->zone_type == "support")
            ? tc.close * (1.0 - stop_loss_pct_ / 100.0)
            : tc.close * (1.0 + stop_loss_pct_ / 100.0);
        sig.take_profit = (staged_->zone_type == "support")
            ? tc.close * (1.0 + take_profit_pct_ / 100.0)
            : tc.close * (1.0 - take_profit_pct_ / 100.0);
        sig.extra = nlohmann::json::object({
            {"zone_level", staged_->zone_level},
            {"zone_type", staged_->zone_type},
        });

        if (staged_->zone_type == "support") {
            since_last_long_ = 0;
        } else {
            since_last_short_ = 0;
        }

        pending_ = sig;

        spdlog::info("SIGNAL: {} {} near {} {} @ {}",
                     sig.symbol, sig.direction, staged_->zone_type,
                     staged_->zone_level, tc.close);
    }

    staged_.reset();
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

    if (candles_since_recalc_ >= recalc_interval_ || support_levels_.empty()) {
        recalcZones();
        candles_since_recalc_ = 0;
    }

    if (support_levels_.empty() && resistance_levels_.empty()) {
        return std::nullopt;
    }

    const OHLCV& cur = candles_.latest();

    if (trend_filter_enabled_) {
        double sma = calcSMA(trend_period_);
        if (sma > 0.0) {
            bool long_allowed = cur.close > sma;
            bool short_allowed = cur.close < sma;
            if (!long_allowed && !short_allowed) {
                return std::nullopt;
            }
        }
    }

    double avg_vol = calcAvgVolume(volume_period_);
    double vol_ratio = (avg_vol > 0.0) ? cur.volume / avg_vol : 1.0;

    if (vol_ratio < volume_mult_) {
        return std::nullopt;
    }

    // ── CHECK SUPPORT (LONG signal) ──
    auto sup = findNearestSupport(cur.low);
    if (sup.has_value() && since_last_long_ >= cooldown_candles_) {
        double level = *sup;
        double dist_pct = (cur.low - level) / level * 100.0;

        if (dist_pct <= wick_threshold_pct_ && cur.close > cur.open) {
            if (confirmation_candles_ > 0) {
                staged_ = PendingSignal{cur, level, "support"};
                since_last_long_ = 0;
                return std::nullopt;
            }

            since_last_long_ = 0;

            Signal sig;
            sig.symbol = cur.symbol;
            sig.timestamp = cur.timestamp;
            sig.direction = "long";
            sig.entry_price = cur.close;
            sig.stop_loss = cur.close * (1.0 - stop_loss_pct_ / 100.0);
            sig.take_profit = cur.close * (1.0 + take_profit_pct_ / 100.0);
            sig.extra = nlohmann::json::object({
                {"zone_level", level},
                {"zone_type", "support"},
                {"volume_ratio", vol_ratio},
                {"distance_pct", dist_pct},
            });

            spdlog::info("SIGNAL: {} LONG near support {} @ {} | dist={:.3f}% volR={:.2f}",
                         cur.symbol, level, cur.close, dist_pct, vol_ratio);
            return sig;
        }
    }

    // ── CHECK RESISTANCE (SHORT signal) ──
    auto res = findNearestResistance(cur.high);
    if (res.has_value() && since_last_short_ >= cooldown_candles_) {
        double level = *res;
        double dist_pct = (level - cur.high) / cur.high * 100.0;

        if (dist_pct <= wick_threshold_pct_ && cur.close < cur.open) {
            if (confirmation_candles_ > 0) {
                staged_ = PendingSignal{cur, level, "resistance"};
                since_last_short_ = 0;
                return std::nullopt;
            }

            since_last_short_ = 0;

            Signal sig;
            sig.symbol = cur.symbol;
            sig.timestamp = cur.timestamp;
            sig.direction = "short";
            sig.entry_price = cur.close;
            sig.stop_loss = cur.close * (1.0 + stop_loss_pct_ / 100.0);
            sig.take_profit = cur.close * (1.0 - take_profit_pct_ / 100.0);
            sig.extra = nlohmann::json::object({
                {"zone_level", level},
                {"zone_type", "resistance"},
                {"volume_ratio", vol_ratio},
                {"distance_pct", dist_pct},
            });

            spdlog::info("SIGNAL: {} SHORT near resistance {} @ {} | dist={:.3f}% volR={:.2f}",
                         cur.symbol, level, cur.close, dist_pct, vol_ratio);
            return sig;
        }
    }

    return std::nullopt;
}

void VolumeProfileSR::recalcZones() {
    volume_map_.clear();

    for (size_t i = 0; i < candles_.size(); ++i) {
        const auto& c = candles_.at(i);

        double body_high = std::max(c.open, c.close);
        double body_low  = std::min(c.open, c.close);

        double body_range = body_high - body_low;
        double lower_wick_range = body_low - c.low;
        double upper_wick_range = c.high - body_high;

        double total_range = c.high - c.low;
        if (total_range <= 0.0) total_range = 1.0;

        double body_share = body_weight_pct_ / 100.0;
        double wick_share = (1.0 - body_share) / 2.0;

        double eff_body  = (body_range > 0.0) ? body_share : 0.0;
        double eff_lower = (lower_wick_range > 0.0) ? wick_share : 0.0;
        double eff_upper = (upper_wick_range > 0.0) ? wick_share : 0.0;

        double missing = (body_share - eff_body) + (wick_share - eff_lower) + (wick_share - eff_upper);
        int active = (body_range > 0.0) + (lower_wick_range > 0.0) + (upper_wick_range > 0.0);
        if (active > 0 && missing > 0.0) {
            double per_segment = missing / active;
            if (eff_body > 0.0)  eff_body  += per_segment;
            if (eff_lower > 0.0) eff_lower += per_segment;
            if (eff_upper > 0.0) eff_upper += per_segment;
        }

        auto distribute = [&](double from, double to, double weight) {
            if (to <= from || weight <= 0.0) return;
            int64_t lo = static_cast<int64_t>(std::floor(from / bucket_size_));
            int64_t hi = static_cast<int64_t>(std::floor((to - 1e-10) / bucket_size_));
            double seg_range = to - from;
            for (int64_t b = lo; b <= hi; ++b) {
                double bl = b * bucket_size_;
                double bh = bl + bucket_size_;
                double overlap = std::min(to, bh) - std::max(from, bl);
                if (overlap > 0.0) {
                    volume_map_[b] += c.volume * weight * (overlap / seg_range);
                }
            }
        };

        if (body_range > 0.0)
            distribute(body_low, body_high, eff_body);
        if (lower_wick_range > 0.0)
            distribute(c.low, body_low, eff_lower);
        if (upper_wick_range > 0.0)
            distribute(body_high, c.high, eff_upper);
    }

    if (volume_map_.empty()) return;

    int64_t min_b = volume_map_.begin()->first;
    int64_t max_b = volume_map_.rbegin()->first;
    int w = static_cast<int>(zone_window_);

    std::vector<std::pair<double, double>> smoothed;
    for (int64_t b = min_b - w; b <= max_b + w; ++b) {
        double sum = 0.0;
        int count = 0;
        for (int64_t nb = b - w; nb <= b + w; ++nb) {
            auto it = volume_map_.find(nb);
            if (it != volume_map_.end()) {
                sum += it->second;
                ++count;
            }
        }
        double avg = (count > 0) ? sum / static_cast<double>(count) : 0.0;
        double price = (b + 0.5) * bucket_size_;
        smoothed.push_back({price, avg});
    }

    support_levels_.clear();
    resistance_levels_.clear();

    double cur_price = candles_.latest().close;
    double peak_volume = 0.0;
    for (const auto& p : smoothed) {
        if (p.second > peak_volume) peak_volume = p.second;
    }

    double effective_min_volume = min_zone_volume_;
    if (min_zone_volume_mode_ == "relative" && peak_volume > 0.0) {
        effective_min_volume = peak_volume * (min_zone_volume_ / 100.0);
    }

    for (size_t i = 1; i + 1 < smoothed.size(); ++i) {
        double prev = smoothed[i - 1].second;
        double cur_v = smoothed[i].second;
        double next = smoothed[i + 1].second;

        if (cur_v > prev && cur_v > next && cur_v >= effective_min_volume) {
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

    // Deduplicate levels that appear in both lists
    std::unordered_set<double> support_set(support_levels_.begin(), support_levels_.end());
    std::unordered_set<double> resistance_set(resistance_levels_.begin(), resistance_levels_.end());

    auto in_both = [&](double level) {
        return support_set.count(level) && resistance_set.count(level);
    };

    support_levels_.erase(
        std::remove_if(support_levels_.begin(), support_levels_.end(), in_both),
        support_levels_.end());
    resistance_levels_.erase(
        std::remove_if(resistance_levels_.begin(), resistance_levels_.end(), in_both),
        resistance_levels_.end());

    spdlog::debug("volume_profile_sr recalc: {} supports, {} resistances from {} candles",
                  support_levels_.size(), resistance_levels_.size(), candles_.size());
}

std::optional<double> VolumeProfileSR::findNearestSupport(double price) const {
    for (double s : support_levels_) {
        if (s <= price) return s;
    }
    return std::nullopt;
}

std::optional<double> VolumeProfileSR::findNearestResistance(double price) const {
    for (double r : resistance_levels_) {
        if (r >= price) return r;
    }
    return std::nullopt;
}

double VolumeProfileSR::calcAvgVolume(size_t period) const {
    if (candles_.size() < period) return 0.0;
    double sum = 0.0;
    for (size_t i = candles_.size() - period; i < candles_.size(); ++i) {
        sum += candles_.at(i).volume;
    }
    return sum / period;
}

double VolumeProfileSR::calcSMA(size_t period) const {
    if (close_prices_.size() < period) return 0.0;
    double sum = 0.0;
    for (size_t i = close_prices_.size() - period; i < close_prices_.size(); ++i) {
        sum += close_prices_.at(i);
    }
    return sum / period;
}
