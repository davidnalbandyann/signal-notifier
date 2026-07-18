#pragma once

#include "strategy_interface.h"

#include <string>

class SignalSender {
public:
    SignalSender(std::string url, int timeout_sec, std::string auth_token);

    bool send(const Signal& s, const std::string& timeframe);

private:
    std::string url_;
    int timeout_ms_;
    std::string auth_token_;
};
