#include "predator_gate.hpp"
#include <openssl/rand.h>
#include <cstring>
#include <algorithm>

namespace burner {

PredatorGate::PredatorGate(bool lock_memory) {
    RAND_bytes(gate_key_.data(), gate_key_.size());
    if (lock_memory) {
        wiper_.mlock_region(gate_key_.data(), gate_key_.size());
    }
}

PredatorGate::~PredatorGate() noexcept {
    destroy();
}

GateResult PredatorGate::birth_token(uint32_t room_id) noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    
    if (burning_.load(std::memory_order_acquire)) {
        return {false, std::nullopt, std::nullopt, 0, true};
    }
    
    auto* fuel = get_or_create_fuel(room_id);
    if (fuel->burned.load(std::memory_order_acquire)) {
        return reject(RejectReason::BURNED, fuel);
    }
    
    if (!fuel->check_rate_limit(MAX_RATE_REQUESTS, RATE_WINDOW_NS)) {
        stats_.record_rate_limit();
        return reject(RejectReason::RATE_LIMIT, fuel);
    }
    fuel->record_request();
    
    expire_old_tokens();
    
    uint32_t room_live = live_count_.count(room_id) ? live_count_[room_id] : 0;
    if (room_live >= MAX_TOKENS_PER_ROOM) {
        return reject(RejectReason::NO_FUEL, fuel);
    }
    
    std::array<uint8_t, NONCE_SIZE> nonce;
    RAND_bytes(nonce.data(), nonce.size());
    
    uint64_t born_at_ns = std::chrono::steady_clock::now().time_since_epoch().count();
    uint64_t seq = sequence_++;
    
    std::array<uint8_t, TOKEN_SIZE> token_value;
    Token::derive_hmac(gate_key_.data(), room_id, born_at_ns, nonce.data(), token_value.data());
    
    Token token{token_value, nonce, room_id, born_at_ns, seq, TokenStatus::LIVE,
                std::chrono::steady_clock::now()};
    
    TokenKey key{token_value};
    tokens_[key] = token;
    live_count_[room_id]++;
    stats_.record_birth(room_id);
    
    return {true, token_value, std::nullopt, fuel->strike_count.load(std::memory_order_acquire), false};
}

GateResult PredatorGate::admit(uint32_t room_id, const uint8_t* token_value) noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    
    if (burning_.load(std::memory_order_acquire)) {
        return {false, std::nullopt, std::nullopt, 0, true};
    }
    
    auto* fuel = get_or_create_fuel(room_id);
    if (fuel->burned.load(std::memory_order_acquire)) {
        return reject(RejectReason::BURNED, fuel);
    }
    
    if (!fuel->check_rate_limit(MAX_RATE_REQUESTS, RATE_WINDOW_NS)) {
        stats_.record_rate_limit();
        return reject(RejectReason::RATE_LIMIT, fuel);
    }
    fuel->record_request();
    
    expire_old_tokens();
    
    TokenKey key;
    std::memcpy(key.bytes.data(), token_value, TOKEN_SIZE);
    
    auto it = tokens_.find(key);
    if (it == tokens_.end()) {
        return reject(RejectReason::NOT_FOUND, fuel);
    }
    
    Token& token = it->second;
    
    if (token.room_id != room_id) return reject(RejectReason::WRONG_ROOM, fuel);
    if (token.status == TokenStatus::CONSUMED) return reject(RejectReason::CONSUMED, fuel);
    if (token.status == TokenStatus::BURNED) return reject(RejectReason::BURNED, fuel);
    if (!token.is_live(TOKEN_MAX_AGE_NS)) {
        token.status = TokenStatus::EXPIRED;
        return reject(RejectReason::EXPIRED, fuel);
    }
    
    auto& seen = seen_sequences_[room_id];
    if (seen.count(token.sequence)) {
        return reject(RejectReason::REPLAYED, fuel);
    }
    
    if (!Token::verify_hmac(gate_key_.data(), token_value, token.room_id,
                           token.born_at_ns, token.nonce.data())) {
        return reject(RejectReason::BAD_HMAC, fuel);
    }
    
    token.status = TokenStatus::CONSUMED;
    seen.insert(token.sequence);
    fuel->reset_strikes();
    stats_.record_admit();
    decrement_live_count(token.room_id);
    wiper_.secure_zero(token.value.data(), token.value.size());
    tokens_.erase(it);
    
    return {true, std::nullopt, std::nullopt, 0, false};
}

GateResult PredatorGate::reject(RejectReason reason, FuelFlow* fuel) noexcept {
    stats_.record_reject(reason);
    uint32_t strikes = fuel ? fuel->increment_strikes() : 0;
    bool burn_triggered = false;
    if (strikes >= MAX_STRIKES) {
        trigger_burn();
        burn_triggered = true;
    }
    return {false, std::nullopt, reason, strikes, burn_triggered};
}

void PredatorGate::expire_old_tokens() noexcept {
    auto it = tokens_.begin();
    while (it != tokens_.end()) {
        Token& token = it->second;
        if (token.status == TokenStatus::LIVE && !token.is_live(TOKEN_MAX_AGE_NS)) {
            token.status = TokenStatus::EXPIRED;
            stats_.record_expire();
            decrement_live_count(token.room_id);
            wiper_.secure_zero(token.value.data(), token.value.size());
            it = tokens_.erase(it);
        } else {
            ++it;
        }
    }
}

void PredatorGate::burn_all_tokens() noexcept {
    for (auto& [key, token] : tokens_) {
        wiper_.secure_zero(token.value.data(), token.value.size());
        wiper_.secure_zero(token.nonce.data(), token.nonce.size());
        token.status = TokenStatus::BURNED;
    }
    stats_.record_wipe(tokens_.size());
    tokens_.clear();
    live_count_.clear();
    wiper_.secure_zero(gate_key_.data(), gate_key_.size());
    for (auto& [id, fuel] : fuel_flows_) fuel->burn();
    wiper_.flush_caches();
}

void PredatorGate::trigger_burn() noexcept {
    burning_.store(true, std::memory_order_release);
    burn_all_tokens();
    stats_.record_burn();
}

void PredatorGate::remove_session(uint32_t terminal_id) noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    fuel_flows_.erase(terminal_id);
    seen_sequences_.erase(terminal_id);
}

bool PredatorGate::is_burning() const noexcept {
    return burning_.load(std::memory_order_acquire);
}

const GateStats& PredatorGate::get_stats() const noexcept {
    return stats_;
}

void PredatorGate::destroy() noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    burn_all_tokens();
    fuel_flows_.clear();
    seen_sequences_.clear();
}

void PredatorGate::decrement_live_count(uint32_t room_id) noexcept {
    auto it = live_count_.find(room_id);
    if (it != live_count_.end() && it->second > 0) {
        it->second--;
        if (it->second == 0) live_count_.erase(it);
    }
}

FuelFlow* PredatorGate::get_or_create_fuel(uint32_t terminal_id) noexcept {
    auto it = fuel_flows_.find(terminal_id);
    if (it == fuel_flows_.end()) {
        it = fuel_flows_.emplace(terminal_id, std::make_unique<FuelFlow>()).first;
    }
    return it->second.get();
}

} // namespace burner
