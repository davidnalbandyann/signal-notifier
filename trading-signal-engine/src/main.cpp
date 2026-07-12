#include "binance_websocket_source.h"
#include "data_source.h"
#include "data_source_interface.h"
#include "utils/json_helpers.h"

#include <csignal>
#include <cstdlib>
#include <iostream>
#include <unordered_map>

#include <nlohmann/json.hpp>
#include <spdlog/spdlog.h>

static std::atomic<bool> g_running{true};

static void handleSignal(int) {
    g_running = false;
    spdlog::warn("signal received, shutting down...");
}

static const std::unordered_map<std::string, spdlog::level::level_enum> LEVEL_MAP = {
    {"trace", spdlog::level::trace},
    {"debug", spdlog::level::debug},
    {"info", spdlog::level::info},
    {"warn", spdlog::level::warn},
    {"error", spdlog::level::err},
    {"critical", spdlog::level::critical},
};

static spdlog::level::level_enum parseLevel(const std::string& s) {
    auto it = LEVEL_MAP.find(s);
    if (it != LEVEL_MAP.end()) return it->second;
    return spdlog::level::info;
}

int main(int argc, char* argv[]) {
    std::signal(SIGINT, handleSignal);
    std::signal(SIGTERM, handleSignal);

    const std::string config_path = (argc > 1) ? argv[1] : "config.json";

    nlohmann::json cfg;
    try {
        cfg = utils::loadConfig(config_path);
    } catch (const std::exception& e) {
        std::cerr << "FATAL: " << e.what() << std::endl;
        return 1;
    }

    auto& log_cfg = cfg["logging"];
    auto level = parseLevel(log_cfg.value("level", std::string("info")));
    spdlog::set_level(level);
    spdlog::set_pattern("[%Y-%m-%d %H:%M:%S.%e] [%^%l%$] %v");

    spdlog::info("config loaded: {}", config_path);

    auto source = std::make_unique<BinanceWebSocketSource>(
        cfg["data_source"]["symbol"].get<std::string>(),
        cfg["data_source"]["timeframe"].get<std::string>()
    );
    source->start();

    spdlog::info("engine running, waiting for candles...");

    while (g_running) {
        OHLCV candle;
        if (source->waitForCandle(candle, 200)) {
            spdlog::info("main: {} close={} ts={}", candle.symbol, candle.close, candle.timestamp);
        }
    }

    source->stop();
    spdlog::info("engine stopped");

    return 0;
}
