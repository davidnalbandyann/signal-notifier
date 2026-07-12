#pragma once

#include "strategy_interface.h"

#include <memory>
#include <nlohmann/json.hpp>

std::unique_ptr<TradingStrategy> createStrategy(const nlohmann::json& cfg);
