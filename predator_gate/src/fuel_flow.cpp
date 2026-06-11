#include "fuel_flow.hpp"

namespace burner {

bool FuelFlow::check_rate_limit(uint32_t max_requests, uint64_t window_ns) noexcept {
    std::lock_guard<std::mutex> lock(rate_mutex);
    auto now = std::chrono::steady_clock::now();
    auto cutoff = now - std::chrono::nanoseconds(window_ns);
    
    while (!request_times.empty() && request_times.front() < cutoff) {
        request_times.pop_front();
    }
    
    return request_times.size() < max_requests;
}

void FuelFlow::record_request() noexcept {
    std::lock_guard<std::mutex> lock(rate_mutex);
    request_times.push_back(std::chrono::steady_clock::now());
}

uint32_t FuelFlow::increment_strikes() noexcept {
    return strike_count.fetch_add(1, std::memory_order_acq_rel) + 1;
}

void FuelFlow::reset_strikes() noexcept {
    strike_count.store(0, std::memory_order_release);
}

void FuelFlow::burn() noexcept {
    burned.store(true, std::memory_order_release);
}

} // namespace burner
