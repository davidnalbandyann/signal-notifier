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

# --- IXWebSocket (WebSocket client for Binance) ---
FetchContent_Declare(
    ixwebsocket
    GIT_REPOSITORY https://github.com/machinezone/IXWebSocket.git
    GIT_TAG v11.4.5
)
set(USE_TLS ON CACHE BOOL "Enable TLS support for IXWebSocket")
FetchContent_MakeAvailable(ixwebsocket)

# --- cpr (HTTP client) ---
find_package(CURL REQUIRED)
FetchContent_Declare(
    cpr
    GIT_REPOSITORY https://github.com/libcpr/cpr.git
    GIT_TAG 1.10.5
)
FetchContent_MakeAvailable(cpr)

# --- M5 target ---
add_executable(trading_signal_engine
    src/main.cpp
    src/data_source.cpp
    src/data_source.h
    src/data_source_interface.h
    src/strategy.cpp
    src/strategy.h
    src/strategy_interface.h
    src/bollinger_squeeze_breakout.cpp
    src/bollinger_squeeze_breakout.h
    src/binance_websocket_source.cpp
    src/binance_websocket_source.h
    src/signal_sender.cpp
    src/signal_sender.h
    src/utils/circular_buffer.h
    src/utils/json_helpers.h
)

target_link_libraries(trading_signal_engine
    PRIVATE
    nlohmann_json::nlohmann_json
    spdlog::spdlog
    ixwebsocket::ixwebsocket
    cpr::cpr
)

target_include_directories(trading_signal_engine PRIVATE src)

# --- Strategy test harness (optional) ---
option(BUILD_TEST_STRATEGY "Build strategy unit test" OFF)
if(BUILD_TEST_STRATEGY)
    add_executable(test_strategy
        src/test_strategy.cpp
        src/bollinger_squeeze_breakout.cpp
        src/bollinger_squeeze_breakout.h
        src/strategy_interface.h
        src/utils/circular_buffer.h
    )
    target_link_libraries(test_strategy
        PRIVATE
        nlohmann_json::nlohmann_json
        spdlog::spdlog
    )
    target_include_directories(test_strategy PRIVATE src)
    add_custom_target(run_test_strategy
        COMMAND $<TARGET_FILE:test_strategy>
        DEPENDS test_strategy
    )
endif()
