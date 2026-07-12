#pragma once

#include "data_source_interface.h"

#include <memory>
#include <nlohmann/json.hpp>

std::unique_ptr<DataSource> createDataSource(const nlohmann::json& cfg);
