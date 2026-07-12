#include "strategy.h"

#include "bollinger_squeeze_breakout.h"

#include <stdexcept>

std::unique_ptr<TradingStrategy> createStrategy(const nlohmann::json& cfg) {
    auto type = cfg.value("type", std::string());

    if (type == "bollinger_squeeze") {
        auto strat = std::make_unique<BollingerSqueezeBreakout>();
        if (cfg.contains("params")) {
            strat->initialize(cfg["params"]);
        }
        return strat;
    }

    throw std::runtime_error("unknown strategy type: " + type);
}
