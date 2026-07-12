#include "data_source_interface.h"
#include "strategy_interface.h"
#include "utils/circular_buffer.h"
#include "utils/json_helpers.h"

#include <nlohmann/json.hpp>
#include <spdlog/spdlog.h>
#include <spdlog/sinks/stdout_color_sinks.h>

#include <iostream>
#include <string>
#include <unordered_map>

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

    auto& ds = cfg["data_source"];
    spdlog::info("data_source: type={} symbol={} timeframe={}",
                 ds["type"].get<std::string>(),
                 ds["symbol"].get<std::string>(),
                 ds["timeframe"].get<std::string>());

    auto& strat = cfg["strategy"];
    spdlog::info("strategy: type={}", strat["type"].get<std::string>());
    for (auto& [k, v] : strat["params"].items()) {
        spdlog::info("  param {} = {}", k, v.dump());
    }

    auto& svc = cfg["python_service"];
    spdlog::info("python_service: url={} timeout={}",
                 svc["url"].get<std::string>(),
                 svc["timeout_sec"].get<int>());

    spdlog::info("engine initialized, waiting for data...");

    CircularBuffer<OHLCV> buffer(5);
    buffer.push({"BTCUSDT", 1000, 60000, 61000, 59000, 60500, 100.0});
    spdlog::info("buffer size={} latest_close={}", buffer.size(), buffer.latest().close);

    return 0;
}
