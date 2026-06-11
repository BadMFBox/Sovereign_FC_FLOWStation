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
