#include "stats.hpp"
#include <mutex>

namespace burner {

static std::mutex stats_map_mutex;

void GateStats::record_birth(uint32_t room_id) noexcept {
    tokens_born.fetch_add(1, std::memory_order_relaxed);
    std::lock_guard<std::mutex> lock(stats_map_mutex);
    tokens_per_room[room_id]++;
}

void GateStats::record_admit() noexcept {
    tokens_admitted.fetch_add(1, std::memory_order_relaxed);
}

void GateStats::record_reject(RejectReason reason) noexcept {
    tokens_rejected.fetch_add(1, std::memory_order_relaxed);
    std::lock_guard<std::mutex> lock(stats_map_mutex);
    rejections_by_reason[reason]++;
}

void GateStats::record_expire() noexcept {
    tokens_expired.fetch_add(1, std::memory_order_relaxed);
}

void GateStats::record_wipe(uint64_t count) noexcept {
    tokens_wiped.fetch_add(count, std::memory_order_relaxed);
}

void GateStats::record_burn() noexcept {
    burns_triggered.fetch_add(1, std::memory_order_relaxed);
}

void GateStats::record_rate_limit() noexcept {
    rate_limits_hit.fetch_add(1, std::memory_order_relaxed);
}

} // namespace burner
