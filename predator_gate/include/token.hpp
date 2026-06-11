#pragma once
#include <cstdint>
#include <array>
#include <chrono>

namespace burner {

constexpr size_t TOKEN_SIZE = 32;
constexpr size_t NONCE_SIZE = 16;

enum class TokenStatus : uint8_t {
    LIVE     = 0x01,
    CONSUMED = 0x02,
    EXPIRED  = 0x03,
    BURNED   = 0x04
};

struct Token {
    std::array<uint8_t, TOKEN_SIZE> value;
    std::array<uint8_t, NONCE_SIZE> nonce;
    uint32_t room_id;
    uint64_t born_at_ns;
    uint64_t sequence;
    TokenStatus status;
    std::chrono::steady_clock::time_point created_at;

    bool is_live(uint64_t max_age_ns) const noexcept;
    uint64_t age_ns() const noexcept;
    uint64_t ttl_ns(uint64_t max_age_ns) const noexcept;

    static void derive_hmac(
        const uint8_t* gate_key,
        uint32_t room_id,
        uint64_t born_at_ns,
        const uint8_t* nonce,
        uint8_t* out_token
    ) noexcept;

    static bool verify_hmac(
        const uint8_t* gate_key,
        const uint8_t* token_value,
        uint32_t room_id,
        uint64_t born_at_ns,
        const uint8_t* nonce
    ) noexcept;
};

} // namespace burner
