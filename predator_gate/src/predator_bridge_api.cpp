#include "predator_bridge_api.hpp"
#include "predator_gate.hpp"
#include <cstring>

extern "C" {

static BurnerReject map_reason(burner::RejectReason r) noexcept {
    switch (r) {
        case burner::RejectReason::NOT_FOUND:   return BURNER_NOT_FOUND;
        case burner::RejectReason::EXPIRED:     return BURNER_EXPIRED;
        case burner::RejectReason::CONSUMED:    return BURNER_CONSUMED;
        case burner::RejectReason::WRONG_ROOM:  return BURNER_WRONG_ROOM;
        case burner::RejectReason::BAD_HMAC:    return BURNER_BAD_HMAC;
        case burner::RejectReason::BURNED:      return BURNER_BURNED;
        case burner::RejectReason::REPLAYED:    return BURNER_REPLAYED;
        case burner::RejectReason::RATE_LIMIT:  return BURNER_RATE_LIMIT;
        case burner::RejectReason::NO_FUEL:     return BURNER_NO_FUEL;
        default:                                return BURNER_SYSTEM_ERR;
    }
}

BURNER_API
void* burner_gate_create(const uint8_t* master_key, size_t key_len) noexcept {
    if (!master_key || key_len < 32) return nullptr;
    try {
        return new burner::PredatorGate(true);
    } catch (...) {
        return nullptr;
    }
}

BURNER_API
int burner_gate_birth_token(
    void*         gate_raw,
    uint32_t      room_id,
    uint8_t*      out_token,
    BurnerReject* reason
) noexcept {
    if (reason) *reason = BURNER_OK;
    if (!gate_raw || !out_token) {
        if (reason) *reason = BURNER_SYSTEM_ERR;
        return 0;
    }

    auto* gate = static_cast<burner::PredatorGate*>(gate_raw);
    auto result = gate->birth_token(room_id);

    if (!result.success) {
        if (reason && result.reject_reason.has_value()) {
            *reason = map_reason(result.reject_reason.value());
        } else if (reason) {
            *reason = BURNER_SYSTEM_ERR;
        }
        return 0;
    }

    if (result.token_value.has_value()) {
        std::memcpy(out_token, result.token_value->data(), 32);
    }
    return 1;
}

BURNER_API
int burner_gate_admit(
    void*          gate_raw,
    uint32_t       room_id,
    const uint8_t* token,
    size_t         token_len,
    BurnerReject*  reason
) noexcept {
    if (reason) *reason = BURNER_OK;
    if (!gate_raw || !token || token_len != 32) {
        if (reason) *reason = BURNER_SYSTEM_ERR;
        return 0;
    }

    auto* gate = static_cast<burner::PredatorGate*>(gate_raw);
    auto result = gate->admit(room_id, token);

    if (!result.success) {
        if (reason && result.reject_reason.has_value()) {
            *reason = map_reason(result.reject_reason.value());
        } else if (reason) {
            *reason = BURNER_SYSTEM_ERR;
        }
        return 0;
    }
    return 1;
}

BURNER_API
void burner_gate_destroy(void* gate_raw) noexcept {
    auto* gate = static_cast<burner::PredatorGate*>(gate_raw);
    if (gate) {
        gate->destroy();
        delete gate;
    }
}

} // extern "C"
