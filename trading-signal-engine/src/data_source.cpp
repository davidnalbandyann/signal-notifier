#include "data_source.h"

#include "binance_rest_source.h"

#include <nlohmann/json.hpp>
#include <stdexcept>

std::unique_ptr<DataSource> createDataSource(const nlohmann::json& cfg) {
    auto type = cfg.value("type", std::string());
    auto symbol = cfg.value("symbol", std::string());
    auto timeframe = cfg.value("timeframe", std::string());

    if (type == "binance") {
        return std::make_unique<BinanceRestSource>(symbol, timeframe);
    }

    throw std::runtime_error("unknown data source type: " + type);
}
