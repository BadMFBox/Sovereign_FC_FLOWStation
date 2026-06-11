"""
core/constants.py

Single source of truth for all configuration values.
"""

BURNER_SLOT_WINDOW    = 10800    # 3 hours
NONCE_SIZE            = 16
TOKEN_SIZE            = 32
HMAC_KEY_SIZE         = 32
BURNER_STRIKE_LIMIT   = 3
BURNER_RATE_WINDOW    = 60
BURNER_RATE_MAX       = 100
BURNER_WIPE_PASSES    = 3
DROP_CACHES_PATH      = "/proc/sys/vm/drop_caches"
CYCLE_DURATION        = 0.27
SLOTS_PER_DAY         = 8
CYCLES_PER_SLOT       = int(BURNER_SLOT_WINDOW / CYCLE_DURATION)
HEALTH_THRESHOLD      = 25

# Aliases — used by burner_gate.py
BURNER_MAX_STRIKES         = BURNER_STRIKE_LIMIT
BURNER_MAX_TOKENS_PER_SLOT = BURNER_RATE_MAX
