#pragma once
#include <cstdint>
#include <string_view>
#include <atomic>
#include <mutex>
#include <cstdio>

namespace burner {

enum class LogLevel : uint8_t {
    DEBUG = 0,
    INFO  = 1,
    WARN  = 2,
    ERROR = 3,
    BURN  = 4
};

constexpr std::string_view to_string(LogLevel level) noexcept {
    switch (level) {
        case LogLevel::DEBUG: return "DEBUG";
        case LogLevel::INFO:  return "INFO ";
        case LogLevel::WARN:  return "WARN ";
        case LogLevel::ERROR: return "ERROR";
        case LogLevel::BURN:  return "BURN ";
        default:              return "?????";
    }
}

class RLog {
public:
    static RLog& instance() noexcept {
        static RLog inst;
        return inst;
    }

    void set_level(LogLevel min_level) noexcept {
        min_level_.store(static_cast<uint8_t>(min_level), std::memory_order_release);
    }

    template<typename... Args>
    void log(LogLevel level, const char* fmt, Args&&... args) noexcept {
        if (static_cast<uint8_t>(level) < min_level_.load(std::memory_order_acquire)) {
            return;
        }
        std::lock_guard<std::mutex> lock(mutex_);
        fprintf(stderr, "[%s] ", to_string(level).data());
        fprintf(stderr, fmt, std::forward<Args>(args)...);
        fprintf(stderr, "\n");
    }

private:
    RLog() = default;
    std::atomic<uint8_t> min_level_{static_cast<uint8_t>(LogLevel::INFO)};
    std::mutex mutex_;
};

} // namespace burner
