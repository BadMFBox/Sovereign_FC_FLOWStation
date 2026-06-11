#!/bin/bash
set -e

# Create directory structure if missing
mkdir -p src include tests cmake

# reject_reason.hpp
cat > include/reject_reason.hpp << 'EOF'
#pragma once
#include <cstdint>
#include <string_view>

namespace burner {

enum class RejectReason : uint8_t {
    NOT_FOUND   = 0x01,
    EXPIRED     = 0x02,
    CONSUMED    = 0x03,
    WRONG_ROOM  = 0x04,
    BAD_HMAC    = 0x05,
    BURNED      = 0x06,
    REPLAYED    = 0x07,
    RATE_LIMIT  = 0x08,
    NO_FUEL     = 0x09
};

constexpr std::string_view to_string(RejectReason reason) noexcept {
    switch(reason) {
        case RejectReason::NOT_FOUND:   return "NOT_FOUND";
        case RejectReason::EXPIRED:     return "EXPIRED";
        case RejectReason::CONSUMED:    return "CONSUMED";
        case RejectReason::WRONG_ROOM:  return "WRONG_ROOM";
        case RejectReason::BAD_HMAC:    return "BAD_HMAC";
        case RejectReason::BURNED:      return "BURNED";
        case RejectReason::REPLAYED:    return "REPLAYED";
        case RejectReason::RATE_LIMIT:  return "RATE_LIMIT";
        case RejectReason::NO_FUEL:     return "NO_FUEL";
        default:                        return "UNKNOWN";
    }
}

} // namespace burner
EOF

# ram_wiper.hpp
cat > include/ram_wiper.hpp << 'EOF'
#pragma once
#include <cstddef>
#include <sys/mman.h>

namespace burner {

class RAMWiper {
public:
    RAMWiper() noexcept = default;
    ~RAMWiper() noexcept;

    bool mlock_region(void* addr, size_t len) noexcept;
    bool munlock_region(void* addr, size_t len) noexcept;
    bool mlock_all() noexcept;
    bool munlock_all() noexcept;
    void secure_zero(void* ptr, size_t len) noexcept;
    void wipe_and_unlock(void* ptr, size_t len) noexcept;
    void flush_caches() noexcept;

private:
    bool all_locked_{false};
};

} // namespace burner
EOF

# ram_wiper.cpp
cat > src/ram_wiper.cpp << 'EOF'
#include "ram_wiper.hpp"
#include <cstring>
#include <sys/mman.h>

namespace burner {

RAMWiper::~RAMWiper() noexcept {
    if (all_locked_) munlock_all();
}

bool RAMWiper::mlock_region(void* addr, size_t len) noexcept {
    if (!addr || len == 0) return false;
    return ::mlock(addr, len) == 0;
}

bool RAMWiper::munlock_region(void* addr, size_t len) noexcept {
    if (!addr || len == 0) return false;
    return ::munlock(addr, len) == 0;
}

bool RAMWiper::mlock_all() noexcept {
    if (::mlockall(MCL_CURRENT | MCL_FUTURE) == 0) {
        all_locked_ = true;
        return true;
    }
    return false;
}

bool RAMWiper::munlock_all() noexcept {
    if (::munlockall() == 0) {
        all_locked_ = false;
        return true;
    }
    return false;
}

void RAMWiper::secure_zero(void* ptr, size_t len) noexcept {
    if (!ptr || len == 0) return;
    volatile uint8_t* vptr = static_cast<volatile uint8_t*>(ptr);
    for (size_t i = 0; i < len; ++i) {
        vptr[i] = 0;
    }
    __asm__ __volatile__("" ::: "memory");
}

void RAMWiper::wipe_and_unlock(void* ptr, size_t len) noexcept {
    secure_zero(ptr, len);
    munlock_region(ptr, len);
}

void RAMWiper::flush_caches() noexcept {
    __asm__ __volatile__("" ::: "memory");
}

} // namespace burner
EOF

echo "✓ All files created"
ls -R
