#pragma once
#include <cstdint>
#include <cstddef>

#if defined(__GNUC__) && __GNUC__ >= 4
    #define BURNER_API __attribute__((visibility("default")))
#else
    #define BURNER_API
#endif

typedef enum BurnerReject {
    BURNER_OK          = 0x00,
    BURNER_NOT_FOUND   = 0x01,
    BURNER_EXPIRED     = 0x02,
    BURNER_CONSUMED    = 0x03,
    BURNER_WRONG_ROOM  = 0x04,
    BURNER_BAD_HMAC    = 0x05,
    BURNER_BURNED      = 0x06,
    BURNER_REPLAYED    = 0x07,
    BURNER_RATE_LIMIT  = 0x08,
    BURNER_NO_FUEL     = 0x09,
    BURNER_SYSTEM_ERR  = 0xFF,
} BurnerReject;

#ifdef __cplusplus
extern "C" {
#endif

BURNER_API void* burner_gate_create(const uint8_t* master_key, size_t key_len) noexcept;

BURNER_API int burner_gate_birth_token(
    void*         gate,
    uint32_t      room_id,
    uint8_t*      out_token,
    BurnerReject* reason
) noexcept;

BURNER_API int burner_gate_admit(
    void*          gate,
    uint32_t       room_id,
    const uint8_t* token,
    size_t         token_len,
    BurnerReject*  reason
) noexcept;

BURNER_API void burner_gate_destroy(void* gate) noexcept;

#ifdef __cplusplus
}
#endif
