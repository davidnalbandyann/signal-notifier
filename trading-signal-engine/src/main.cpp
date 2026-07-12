#include "binance_websocket_source.h"
#include "data_source.h"
#include "signal_sender.h"
#include "strategy.h"
#include "utils/json_helpers.h"

#include <csignal>
#include <cstdlib>
#include <iostream>
#include <unordered_map>

#include <nlohmann/json.hpp>
#include <spdlog/spdlog.h>

static std::atomic<bool> g_running{true};
static DataSource* g_source{nullptr};

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

    // Instantiate pipeline
    auto source = createDataSource(cfg["data_source"]);
    g_source = source.get();

    auto strategy = createStrategy(cfg["strategy"]);

    auto& svc = cfg["python_service"];
    SignalSender sender(
        svc["url"].get<std::string>(),
        svc["timeout_sec"].get<int>(),
        svc.value("auth_token", std::string())
    );

    std::string timeframe = cfg["data_source"].value("timeframe", std::string("15m"));

    source->start();
    spdlog::info("engine running, waiting for candles...");

    while (g_running) {
        OHLCV candle;

        // waitForCandle is specific to BinanceWebSocketSource; use dynamic_cast
        auto* ws = dynamic_cast<BinanceWebSocketSource*>(source.get());
        bool got = false;
        if (ws) {
            got = ws->waitForCandle(candle, 200);
        } else {
            std::this_thread::sleep_for(std::chrono::milliseconds(200));
        }

        if (!g_running) break;

        if (got) {
            strategy->onCandle(candle);

            if (auto sig = strategy->checkSignal()) {
                sender.send(*sig, timeframe);
            }
        }
    }

    source->stop();
    spdlog::info("engine stopped");

    return 0;
}
