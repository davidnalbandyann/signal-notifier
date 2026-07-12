#pragma once

#include <fstream>
#include <nlohmann/json.hpp>
#include <stdexcept>
#include <string>

namespace utils {

inline nlohmann::json loadConfig(const std::string& path) {
    std::ifstream file(path);
    if (!file.is_open()) {
        throw std::runtime_error("cannot open config file: " + path);
    }
    try {
        return nlohmann::json::parse(file);
    } catch (const nlohmann::json::parse_error& e) {
        throw std::runtime_error("config parse error in " + path + ": " + e.what());
    }
}

} // namespace utils
