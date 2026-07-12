cmake_minimum_required(VERSION 3.16)
project(trading_signal_engine LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR})

include(FetchContent)

# nlohmann/json
FetchContent_Declare(
    json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.11.3
)
FetchContent_MakeAvailable(json)

# spdlog
FetchContent_Declare(
    spdlog
    GIT_REPOSITORY https://github.com/gabime/spdlog.git
    GIT_TAG v1.13.0
)
FetchContent_MakeAvailable(spdlog)

# --- Minimal M1 target (no WS / HTTP yet) ---
add_executable(trading_signal_engine
    src/main.cpp
    src/data_source_interface.h
    src/strategy_interface.h
    src/utils/circular_buffer.h
    src/utils/json_helpers.h
)

target_link_libraries(trading_signal_engine
    PRIVATE
    nlohmann_json::nlohmann_json
    spdlog::spdlog
)

target_include_directories(trading_signal_engine PRIVATE src)
