#include "signal_sender.h"

#include <cpr/cpr.h>
#include <nlohmann/json.hpp>
#include <spdlog/spdlog.h>

SignalSender::SignalSender(std::string url, int timeout_sec, std::string auth_token)
    : url_(std::move(url)),
      timeout_ms_(timeout_sec * 1000),
      auth_token_(std::move(auth_token)) {}

bool SignalSender::send(const Signal& s, const std::string& timeframe) {
    nlohmann::json payload;
    payload["symbol"] = s.symbol;
    payload["timestamp"] = s.timestamp;
    payload["direction"] = s.direction;
    payload["entry_price"] = s.entry_price;
    payload["timeframe"] = timeframe;
    payload["extra"] = s.extra;

    std::string body = payload.dump();

    cpr::Header headers{{"Content-Type", "application/json"}};
    if (!auth_token_.empty()) {
        headers["X-Trigger-Token"] = auth_token_;
    }

    spdlog::info("sending signal to {}: {}", url_, body);

    try {
        auto r = cpr::Post(
            cpr::Url{url_},
            cpr::Body{body},
            headers,
            cpr::Timeout{timeout_ms_}
        );

        if (r.status_code == 200) {
            spdlog::info("signal sent OK: status={} body={}",
                         r.status_code, r.text.substr(0, 300));
            return true;
        }

        spdlog::warn("signal send returned {}: {}", r.status_code, r.text.substr(0, 300));
    } catch (const std::exception& e) {
        spdlog::error("signal send failed: {}", e.what());
    }

    return false;
}
