#pragma once
#include <cstdint>
#include <atomic>
#include <chrono>
#include <mutex>
#include <deque>

namespace burner {

struct FuelFlow {
    std::atomic<bool> burned{false};
    std::atomic<uint64_t> last_seq{0};
    std::atomic<uint32_t> strike_count{0};
    
    mutable std::mutex rate_mutex;
    std::deque<std::chrono::steady_clock::time_point> request_times;
    
    bool check_rate_limit(uint32_t max_requests, uint64_t window_ns) noexcept;
    void record_request() noexcept;
    uint32_t increment_strikes() noexcept;
    void reset_strikes() noexcept;
    void burn() noexcept;
};

} // namespace burner
