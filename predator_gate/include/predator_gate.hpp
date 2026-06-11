#pragma once
#include <array>
#include <unordered_map>
#include <unordered_set>
#include <mutex>
#include <memory>
#include <optional>
#include "token.hpp"
#include "reject_reason.hpp"
#include "fuel_flow.hpp"
#include "stats.hpp"
#include "ram_wiper.hpp"

namespace burner {

constexpr uint64_t TOKEN_MAX_AGE_NS = 30'000'000'000ULL;
constexpr uint32_t MAX_STRIKES = 3;
constexpr uint32_t MAX_TOKENS_PER_ROOM = 3;
constexpr uint32_t MAX_RATE_REQUESTS = 100;
constexpr uint64_t RATE_WINDOW_NS = 1'000'000'000ULL;

struct TokenKey {
    std::array<uint8_t, TOKEN_SIZE> bytes;
    bool operator==(const TokenKey& o) const noexcept {
        return bytes == o.bytes;
    }
};

struct TokenKeyHash {
    size_t operator()(const TokenKey& k) const noexcept {
        size_t h = 14695981039346656037ULL;
        for (uint8_t b : k.bytes) {
            h ^= b;
            h *= 1099511628211ULL;
        }
        return h;
    }
};

struct GateResult {
    bool success;
    std::optional<std::array<uint8_t, TOKEN_SIZE>> token_value;
    std::optional<RejectReason> reject_reason;
    uint32_t strikes;
    bool burn_triggered;
};

class PredatorGate {
public:
    explicit PredatorGate(bool lock_memory = true);
    ~PredatorGate() noexcept;

    GateResult birth_token(uint32_t room_id) noexcept;
    GateResult admit(uint32_t room_id, const uint8_t* token_value) noexcept;
    void remove_session(uint32_t terminal_id) noexcept;
    bool is_burning() const noexcept;
    void trigger_burn() noexcept;
    const GateStats& get_stats() const noexcept;
    void destroy() noexcept;

private:
    std::array<uint8_t, 32> gate_key_;
    std::unordered_map<TokenKey, Token, TokenKeyHash> tokens_;
    std::unordered_map<uint32_t, uint32_t> live_count_;
    std::unordered_map<uint32_t, std::unordered_set<uint64_t>> seen_sequences_;
    std::unordered_map<uint32_t, std::unique_ptr<FuelFlow>> fuel_flows_;
    uint64_t sequence_{0};
    std::atomic<bool> burning_{false};
    RAMWiper wiper_;
    GateStats stats_;
    mutable std::mutex mutex_;

    GateResult reject(RejectReason reason, FuelFlow* fuel) noexcept;
    void expire_old_tokens() noexcept;
    void burn_all_tokens() noexcept;
    void decrement_live_count(uint32_t room_id) noexcept;
    FuelFlow* get_or_create_fuel(uint32_t terminal_id) noexcept;
};

} // namespace burner
