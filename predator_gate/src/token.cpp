#include "token.hpp"
#include <openssl/hmac.h>
#include <openssl/evp.h>
#include <cstring>
#include <arpa/inet.h>

#if defined(__ANDROID__) || defined(__linux__)
#include <endian.h>
#endif

namespace burner {

bool Token::is_live(uint64_t max_age_ns) const noexcept {
    if (status != TokenStatus::LIVE) return false;
    return age_ns() <= max_age_ns;
}

uint64_t Token::age_ns() const noexcept {
    auto now = std::chrono::steady_clock::now();
    auto elapsed = now - created_at;
    return std::chrono::duration_cast<std::chrono::nanoseconds>(elapsed).count();
}

uint64_t Token::ttl_ns(uint64_t max_age_ns) const noexcept {
    uint64_t age = age_ns();
    return (age < max_age_ns) ? (max_age_ns - age) : 0;
}

void Token::derive_hmac(
    const uint8_t* gate_key,
    uint32_t room_id,
    uint64_t born_at_ns,
    const uint8_t* nonce,
    uint8_t* out_token
) noexcept {
    uint8_t msg[28];
    uint32_t room_id_be = htonl(room_id);
    uint64_t born_be = htobe64(born_at_ns);
    
    std::memcpy(msg, &room_id_be, 4);
    std::memcpy(msg + 4, &born_be, 8);
    std::memcpy(msg + 12, nonce, NONCE_SIZE);

    unsigned int len = TOKEN_SIZE;
    HMAC(EVP_sha256(), gate_key, 32, msg, 28, out_token, &len);
}

bool Token::verify_hmac(
    const uint8_t* gate_key,
    const uint8_t* token_value,
    uint32_t room_id,
    uint64_t born_at_ns,
    const uint8_t* nonce
) noexcept {
    uint8_t expected[TOKEN_SIZE];
    derive_hmac(gate_key, room_id, born_at_ns, nonce, expected);
    return CRYPTO_memcmp(expected, token_value, TOKEN_SIZE) == 0;
}

} // namespace burner
