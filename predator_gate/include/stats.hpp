#pragma once
#include <cstdint>
#include <atomic>
#include <unordered_map>
#include "reject_reason.hpp"

namespace burner {

struct GateStats {
    std::atomic<uint64_t> tokens_born{0};
    std::atomic<uint64_t> tokens_admitted{0};
    std::atomic<uint64_t> tokens_rejected{0};
    std::atomic<uint64_t> tokens_expired{0};
    std::atomic<uint64_t> tokens_wiped{0};
    std::atomic<uint64_t> burns_triggered{0};
    std::atomic<uint64_t> rate_limits_hit{0};
    
    std::unordered_map<uint32_t, uint64_t> tokens_per_room;
    std::unordered_map<RejectReason, uint64_t> rejections_by_reason;
    
    void record_birth(uint32_t room_id) noexcept;
    void record_admit() noexcept;
    void record_reject(RejectReason reason) noexcept;
    void record_expire() noexcept;
    void record_wipe(uint64_t count = 1) noexcept;
    void record_burn() noexcept;
    void record_rate_limit() noexcept;
};

} // namespace burner
