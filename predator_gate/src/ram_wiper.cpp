#include "ram_wiper.hpp"
#include <cstdint>
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
