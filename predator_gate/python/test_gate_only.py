#!/usr/bin/env python3
"""
Standalone gate verification test.
Does NOT require Room Zero or full mesh.
Only tests:
  1. C++ gate loads
  2. Python bridge can call it
  3. Strike counting works
  4. Burn triggers on 3 strikes
"""

import sys
from predator_bridge import PredatorBridge, RejectReason, BurnerError

print("=" * 60)
print("PREDATOR GATE — STANDALONE VERIFICATION")
print("=" * 60)

# ── TEST 1: Load master key ──────────────────────────────
print("\n[TEST 1] Loading master key from master.key...")
try:
    with open('master.key', 'rb') as f:
        key = f.read()
    
    if len(key) != 32:
        print(f"✗ FAIL — key is {len(key)} bytes, expected 32")
        sys.exit(1)
    
    print(f"  ✓ PASS — 32-byte key loaded")
except FileNotFoundError:
    print("✗ FAIL — master.key not found")
    sys.exit(1)

# ── TEST 2: Create gate instance ─────────────────────────
print("\n[TEST 2] Creating PredatorBridge instance...")
try:
    gate = PredatorBridge(master_key=key)
    print("  ✓ PASS — gate created")
except Exception as e:
    print(f"✗ FAIL — {e}")
    sys.exit(1)

# ── TEST 3: Valid token admission ───────────────────────
print("\n[TEST 3] Testing valid token admission...")
valid_token = b"VALID_TOKEN_32BYTES_PADDING_HER"  # 32 bytes
try:
    gate.admit(room_id=1, token=valid_token)
    print("  ✓ PASS — valid token accepted")
except BurnerError as e:
    print(f"✗ FAIL — valid token rejected: {e}")
    sys.exit(1)

# ── TEST 4: Invalid token (strike 1) ─────────────────────
print("\n[TEST 4] Testing invalid token (strike 1)...")
bad_token = b"BAD_TOKEN_" + b"X" * 22  # 32 bytes but wrong
try:
    gate.admit(room_id=1, token=bad_token)
    print("✗ FAIL — bad token was accepted (should reject)")
    sys.exit(1)
except BurnerError as e:
    if e.reason in (RejectReason.INVALID_TOKEN, RejectReason.INVALID_MAC):
        print(f"  ✓ PASS — rejected with {e.reason.name}")
    else:
        print(f"✗ FAIL — wrong rejection reason: {e.reason.name}")
        sys.exit(1)

# ── TEST 5: Second bad token (strike 2) ──────────────────
print("\n[TEST 5] Testing second bad token (strike 2)...")
try:
    gate.admit(room_id=1, token=bad_token)
    print("✗ FAIL — bad token accepted on strike 2")
    sys.exit(1)
except BurnerError as e:
    if e.reason in (RejectReason.INVALID_TOKEN, RejectReason.INVALID_MAC):
        print(f"  ✓ PASS — rejected with {e.reason.name}")
    else:
        print(f"✗ FAIL — wrong rejection reason: {e.reason.name}")
        sys.exit(1)

# ── TEST 6: Third bad token (strike 3 → BURN) ────────────
print("\n[TEST 6] Testing third bad token (strike 3 → BURN)...")
try:
    gate.admit(room_id=1, token=bad_token)
    print("✗ FAIL — gate did not burn after 3 strikes")
    sys.exit(1)
except BurnerError as e:
    if e.reason == RejectReason.BURNED:
        print(f"  ✓ PASS — gate burned after 3 strikes")
    else:
        print(f"✗ FAIL — expected BURNED, got {e.reason.name}")
        sys.exit(1)

# ── TEST 7: Post-burn behavior ───────────────────────────
print("\n[TEST 7] Testing post-burn rejection...")
try:
    gate.admit(room_id=1, token=valid_token)
    print("✗ FAIL — gate accepted token after burn")
    sys.exit(1)
except BurnerError as e:
    if e.reason == RejectReason.BURNED:
        print(f"  ✓ PASS — post-burn rejection confirmed")
    else:
        print(f"✗ FAIL — expected BURNED, got {e.reason.name}")
        sys.exit(1)

# ── TEST 8: Cleanup ──────────────────────────────────────
print("\n[TEST 8] Gate cleanup...")
try:
    gate.destroy()
    print("  ✓ PASS — gate destroyed cleanly")
except Exception as e:
    print(f"✗ FAIL — cleanup error: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("ALL TESTS PASSED ✓")
print("Predator gate is operational.")
print("=" * 60)
