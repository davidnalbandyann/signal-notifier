#include "data_source.h"
#include "signal_sender.h"
#include "strategy.h"
#include "utils/json_helpers.h"

#include <chrono>
#include <csignal>
#include <cstdlib>
#include <ctime>
#include <iostream>
#include <thread>
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

    // Set timezone for log timestamps (uses TZ env var + localtime)
    std::string tz = log_cfg.value("timezone", std::string());
    if (!tz.empty()) {
        setenv("TZ", tz.c_str(), 1);
        tzset();
        spdlog::debug("timezone set: {}", tz);
    }

    spdlog::set_level(level);
    spdlog::set_pattern("[%Y-%m-%d %H:%M:%S.%e] [%^%l%$] %v");

    spdlog::info("config loaded: {}", config_path);

    std::string webhook_url = cfg.value("webhook_url", std::string("http://127.0.0.1:8000/trigger"));
    int timeout_sec = 35;
    std::string auth_token = "";
    
    if (cfg.contains("python_service")) {
        auto& svc = cfg["python_service"];
        webhook_url = svc.value("url", webhook_url);
        timeout_sec = svc.value("timeout_sec", timeout_sec);
        auth_token = svc.value("auth_token", auth_token);
    }
    
    SignalSender sender(webhook_url, timeout_sec, auth_token);

    struct Pipeline {
        int active_strategy_id;
        std::string name;
        std::string symbol;
        std::string timeframe;
        std::unique_ptr<DataSource> source;
        std::unique_ptr<TradingStrategy> strategy;
    };

    std::vector<Pipeline> pipelines;

    if (cfg.contains("strategies") && cfg["strategies"].is_array()) {
        for (auto& s_cfg : cfg["strategies"]) {
            Pipeline p;
            p.active_strategy_id = s_cfg.value("active_strategy_id", 0);
            p.name = s_cfg.value("active_strategy_name", "unnamed");
            p.symbol = s_cfg.value("symbol", "BTCUSDT");
            p.timeframe = s_cfg.value("timeframe", "15m");
            
            nlohmann::json ds_cfg;
            ds_cfg["type"] = "binance";
            ds_cfg["symbol"] = p.symbol;
            ds_cfg["timeframe"] = p.timeframe;
            
            p.source = createDataSource(ds_cfg);
            p.strategy = createStrategy(s_cfg);
            
            pipelines.push_back(std::move(p));
        }
    } else if (cfg.contains("strategy") && cfg.contains("data_source")) {
        // legacy config support
        Pipeline p;
        p.active_strategy_id = 0;
        p.name = "legacy";
        p.symbol = cfg["data_source"].value("symbol", "BTCUSDT");
        p.timeframe = cfg["data_source"].value("timeframe", "15m");
        p.source = createDataSource(cfg["data_source"]);
        p.strategy = createStrategy(cfg["strategy"]);
        pipelines.push_back(std::move(p));
    }

    if (pipelines.empty()) {
        spdlog::warn("No pipelines configured. Exiting.");
        return 0;
    }

    for (auto& p : pipelines) {
        p.source->start();
    }
    spdlog::info("engine running with {} active pipelines...", pipelines.size());

    while (g_running) {
        for (auto& p : pipelines) {
            OHLCV candle;
            if (p.source->pollCandle(candle)) {
                spdlog::info("[{}] candle: {} close={} ts={} vol={}",
                             p.active_strategy_id, candle.symbol, candle.close, candle.timestamp, candle.volume);
                p.strategy->onCandle(candle);
                if (auto sig = p.strategy->checkSignal()) {
                    sig->active_strategy_id = p.active_strategy_id;
                    sender.send(*sig, p.timeframe);
                }
            }
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(1000));
    }

    for (auto& p : pipelines) {
        p.source->stop();
    }
    spdlog::info("engine stopped");

    return 0;
}
