#!/usr/bin/env python3
"""
FlowStation v1.1.0 — FC_FLOW
Fuel Command Flow Line Own-Stack Withholding
Sovereign Fuel Mesh | 8CV (8-Core-Velocity) Reactive Engine

SINGLE FILE VERSION — For Termux / Direct Execution
Run: python3 FlowStation-v1.1.0-FC_FLOW.py
"""

import os
import sys
import json
import time
import hashlib
import secrets
import socket
import struct
import base64
import shutil
import difflib
import logging
import threading
import asyncio
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, Dict, List, Set
from dataclasses import dataclass, field
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# ══════════════════════════════════════════════════════════
# CORE
# ══════════════════════════════════════════════════════════


# ── CONSTANTS ──


# ── Version ───────────────────────────────────────────────
VERSION = "1.1.0-fcflow"

# ── 8CV Timing ──────────────────────────────────────────────
CYCLE_INTERVAL = 0.27          # 8CV loop tick
GRACE_CYCLES = 15              # boot grace for 8CV warmup
HEALTHY_CYCLES = 222           # healthy run threshold

# ── Crypto ──────────────────────────────────────────────────
KEY_SIZE = 32
REPLAY_WINDOW = 50

# ── Health ──────────────────────────────────────────────────
HEALTH_HISTORY = 50

# ── Feeds ───────────────────────────────────────────────────
MAX_FEED_EVENTS = 100

# ── Web ─────────────────────────────────────────────────────
WEB_HOST = "0.0.0.0"
WEB_PORT = 8080
WS_PORT = 8081
MAX_WS_CLIENTS = 8
WS_BROADCAST_HZ = 4

# ── Paths ───────────────────────────────────────────────────
VAULT_DIR = "vault"            # FuelStation Token Vault
PHASES_DIR = "phases"
EXPORT_DIR = "exports"
FEEDS_DIR = "ai_feeds"
SHARED_DIR = "shared"
ROOMS_DIR = "rooms"
AUDIT_LOG = "shared/audit.log"
PIN_PATH = "shared/.pin"
CONTEXT_PATH = "shared/ai_access.json"
LOCK_STORE = "shared/logic_lock.json"
ROSTER_PATH = "shared/ai_roster.json"
ASSIGN_PATH = "shared/room_assignments.json"
COMMANDER_LOG = "shared/commander.log"
KEY_FILES = [PIN_PATH, AUDIT_LOG, CONTEXT_PATH]

# ── 8CV Room Topology — Sovereign Fuel Mesh ───────────────
# R0: Sovereign Fuel  — Core power, entropy source for all 8CV loops
# R1: Logic Lock      — Auth & access control, top loop giver
# R2: EvoFuse         — HUB, encodes both loops, AI fusion brain
# R3: Pass Patrol     — Shared node, crossover, credential monitoring
# R4: Flow Control    — Bottom loop giver
# R5: AiZquad         — Bottom loop giver

ROOMS = {
    "room_0": "SovereignFuel",
    "room_1": "LogicLock",
    "room_2": "EvoFuse",
    "room_3": "PassPatrol",
    "room_4": "FlowControl",
    "room_5": "AiZquad",
}

# ── 8CV Loop Topology — FC_FLOW Figure-8 ───────────────────
# BOTTOM: R4(Flow) + R5(AiZquad) → R2(EvoFuse encodes) → R3(PassPatrol decodes+adds) → back
# TOP:    R1(LogicLock) + R3(PassPatrol) → R2(EvoFuse encodes) → R1(LogicLock decodes) → back
# HUB:    R2 EvoFuse — the AI fusion brain
# POWER:  R0 Sovereign Fuel — feeds key entropy into every room

BOTTOM_GIVERS = ["room_4", "room_5"]   # FlowControl + AiZquad
HUB = "room_2"                         # EvoFuse — encoding hub
BOTTOM_DECODER = "room_3"               # PassPatrol — decodes bottom

TOP_GIVERS = ["room_1", "room_3"]       # LogicLock + PassPatrol
TOP_DECODER = "room_1"                   # LogicLock — decodes top

# Backward compat aliases
TOP_LOOP = ["room_1", "room_2", "room_3"]
BOTTOM_LOOP = ["room_4", "room_5", "room_3"]

# ── AI Team — FC_FLOW Operators ─────────────────────────────
AI_TEAM = {
    "kiro":   "System architect",
    "claude": "Code review and security",
    "gpt":    "Documentation and planning",
    "gemini": "Testing and validation",
}


# ── ENUMS ──




class GearState(Enum):
    """8CV gear states — undisputed token flow control."""
    GEAR_1_STANDBY = 1
    GEAR_2_ACTIVE = 2
    GEAR_3_UNDISPUTED = 3


class BuzzkillTier(Enum):
    """Buzzkill tiers — FC_FLOW custom sigkill escalation."""
    TIER_1_SURGICAL = 1
    TIER_2_SCORCHED = 2
    TIER_3_LIVE_BURN = 3


class LoopStatus(Enum):
    """8CV loop health status."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    FAILED = "FAILED"


class OptimizerMode(Enum):
    """FC_FLOW reactive optimizer modes."""
    IDLE = "IDLE"
    NORMAL = "NORMAL"
    THROTTLE = "THROTTLE"
    SURGE = "SURGE"


# ── MODELS ──





@dataclass
class LoopHealthReport:
    """8CV health snapshot per cycle."""
    timestamp: float
    cycle_id: str
    health_score: int
    top_loop: LoopStatus
    bottom_loop: LoopStatus
    buzzkill_trigger: Optional[BuzzkillTier] = None
    failure_details: str = ""


@dataclass
class RoomKeyStore:
    """FuelStation Token Vault — per-room key material."""
    room_id: str
    seed: bytes = field(default_factory=lambda: bytes(32))
    split: bytes = field(default_factory=lambda: bytes(32))
    generated: float = 0.0

    def wipe(self):
        """Burn key material — buzzkill ready."""
        self.seed = bytes(32)
        self.split = bytes(32)


@dataclass
class CommanderAlert:
    """FC_FLOW commander alert."""
    timestamp: str
    event: str
    detail: str
    severity: str


@dataclass
class OptimizerState:
    """FC_FLOW reactive optimizer snapshot."""
    token_rate: float = 0.0
    connection_load: int = 0
    cycle_pressure: float = 0.0
    mode: OptimizerMode = OptimizerMode.NORMAL
    batch_count: int = 0


# ── AUDIT ──




_audit_lock = threading.Lock()


def write_audit(event: str, detail: str = ""):
    """Thread-safe FC_FLOW audit write."""
    try:
        os.makedirs(SHARED_DIR, exist_ok=True)
        with _audit_lock:
            with open(AUDIT_LOG, 'a') as f:
                f.write(
                    f"{datetime.now().isoformat()} "
                    f"[{event}] {detail}\n"
                )
    except Exception as e:
        logging.getLogger("FlowStation").warning(f"Audit write failed: {e}")


# ── KEY STORE ──





class KeyStore:
    """Manages key material for all rooms in the Sovereign Fuel mesh."""

    def __init__(self):
        self._stores: Dict[str, RoomKeyStore] = {
            r: RoomKeyStore(room_id=r) for r in ROOMS
        }

    def get(self, room_id: str) -> RoomKeyStore:
        return self._stores[room_id]

    def all_splits(self) -> Dict[str, bytes]:
        return {r: s.split for r, s in self._stores.items()}

    def rotate(self, room_state_feeds: dict = None, room_threat_feeds: dict = None):
        """Rotate keys with 8CV topology awareness."""
        for room_id, store in self._stores.items():
            entropy = secrets.token_bytes(KEY_SIZE)
            state = self._get_room_state(room_id, room_state_feeds)
            threat = self._get_room_threat(room_id, room_threat_feeds)
            seed = hashlib.sha256(entropy + state + threat).digest()
            salt = hashlib.sha256(
                room_id.encode() + b"fcflow_8cv"
            ).digest()
            split = hashlib.sha256(seed + salt).digest()
            store.seed = seed
            store.split = split
            store.generated = time.monotonic()

    def wipe_all(self):
        """Burn all key material — buzzkill ready."""
        for store in self._stores.values():
            store.wipe()

    def _get_room_state(self, room_id: str, feeds: dict = None) -> bytes:
        if feeds and room_id in feeds:
            try:
                return feeds[room_id]()
            except Exception:
                pass
        data = room_id.encode() + str(time.monotonic()).encode()
        return hashlib.sha256(data).digest()

    def _get_room_threat(self, room_id: str, feeds: dict = None) -> int:
        if feeds and room_id in feeds:
            try:
                return feeds[room_id]()
            except Exception:
                pass
        return 0


# ── LOOPS ──






class LoopValidator:
    """Validates 8CV loops with proper FC_FLOW topology."""

    def __init__(self, key_store: "KeyStore"):
        self._keys = key_store

    def validate_bottom(self) -> LoopStatus:
        """
        BOTTOM 8CV LOOP:
          R4(FlowControl) + R5(AiZquad) → R2(EvoFuse encodes)
          → R3(PassPatrol decodes+adds) → back to R4/R5
        """
        try:
            null = bytes(KEY_SIZE)

            r2 = self._keys.get(HUB).split
            r3 = self._keys.get(BOTTOM_DECODER).split
            r4 = self._keys.get(BOTTOM_GIVERS[0]).split
            r5 = self._keys.get(BOTTOM_GIVERS[1]).split

            # Boot guard
            if any(s == null for s in [r2, r3, r4, r5]):
                return LoopStatus.DEGRADED

            # Step 1 — R4 + R5 give keys to R2
            bottom_input = bytes(a ^ b for a, b in zip(r4, r5))
            if bottom_input == null:
                return LoopStatus.FAILED  # R4 == R5 = compromise

            # Step 2 — R2 encodes (combines + adds its key)
            encoded = hashlib.sha256(bottom_input + r2).digest()
            if encoded == null:
                return LoopStatus.FAILED

            # Step 3 — R3 decodes + adds its own key
            r3_output = hashlib.sha256(encoded + r3).digest()
            if r3_output == null:
                return LoopStatus.FAILED

            # Entropy check
            e1 = sum(bin(b).count('1') for b in bottom_input)
            e2 = sum(bin(b).count('1') for b in encoded)
            e3 = sum(bin(b).count('1') for b in r3_output)

            if min(e1, e2, e3) < 64:
                return LoopStatus.CRITICAL
            if min(e1, e2, e3) < 96:
                return LoopStatus.DEGRADED
            return LoopStatus.HEALTHY

        except Exception as exc:
            logging.getLogger("8CV").error(f"Bottom loop validation error: {exc}")
            return LoopStatus.FAILED

    def validate_top(self) -> LoopStatus:
        """
        TOP 8CV LOOP (criss-cross):
          R1(LogicLock) + R3(PassPatrol) → R2(EvoFuse encodes)
          → R1(LogicLock decodes) → loops back
        """
        try:
            null = bytes(KEY_SIZE)

            r1 = self._keys.get(TOP_GIVERS[0]).split
            r2 = self._keys.get(HUB).split
            r3 = self._keys.get(TOP_GIVERS[1]).split

            if any(s == null for s in [r1, r2, r3]):
                return LoopStatus.DEGRADED

            # Step 1 — R1 + R3 give keys to R2 (criss-cross)
            # XOR order reversed vs bottom = the criss-cross asymmetry
            top_input = bytes(a ^ b for a, b in zip(r3, r1))
            if top_input == null:
                return LoopStatus.FAILED  # R1 == R3 = compromise

            # Step 2 — R2 encodes the top loop
            encoded = hashlib.sha256(r2 + top_input).digest()
            if encoded == null:
                return LoopStatus.FAILED

            # Step 3 — R1 decodes
            r1_output = hashlib.sha256(encoded + r1).digest()
            if r1_output == null:
                return LoopStatus.FAILED

            e1 = sum(bin(b).count('1') for b in top_input)
            e2 = sum(bin(b).count('1') for b in encoded)
            e3 = sum(bin(b).count('1') for b in r1_output)

            if min(e1, e2, e3) < 64:
                return LoopStatus.CRITICAL
            if min(e1, e2, e3) < 96:
                return LoopStatus.DEGRADED
            return LoopStatus.HEALTHY

        except Exception as exc:
            logging.getLogger("8CV").error(f"Top loop validation error: {exc}")
            return LoopStatus.FAILED


# ── CROSSOVER ──






class CrossoverValidator:
    """Validates the figure-8 crossover point where loops meet."""

    def __init__(self, key_store: "KeyStore"):
        self._keys = key_store

    def validate(self, cycle_count: int) -> bool:
        """
        FIGURE-8 CROSS-VALIDATION.

        The 8CV figure-8 is valid when:
        1. R2 (EvoFuse hub) can bind both loops consistently.
        2. R3 (PassPatrol shared node) — its output from bottom loop
           is consistent with its input to top loop.
        3. The combined figure-8 token has sufficient entropy.
        """
        try:
            null = bytes(KEY_SIZE)
            in_grace = cycle_count <= GRACE_CYCLES

            r1 = self._keys.get(TOP_GIVERS[0]).split
            r2 = self._keys.get(HUB).split
            r3 = self._keys.get(BOTTOM_DECODER).split
            r4 = self._keys.get(BOTTOM_GIVERS[0]).split
            r5 = self._keys.get(BOTTOM_GIVERS[1]).split

            if any(s == null for s in [r1, r2, r3, r4, r5]):
                return False  # Not generated yet — grace handles it

            # ── Bottom loop derivation ─────────────────────
            bottom_input = bytes(a ^ b for a, b in zip(r4, r5))
            bottom_enc = hashlib.sha256(bottom_input + r2).digest()
            bottom_r3_out = hashlib.sha256(bottom_enc + r3).digest()

            # ── Top loop derivation ──────────────────────────
            # Criss-cross: r3 XOR r1, reversed order vs bottom
            top_input = bytes(a ^ b for a, b in zip(r3, r1))
            top_enc = hashlib.sha256(r2 + top_input).digest()
            top_r1_out = hashlib.sha256(top_enc + r1).digest()

            # ── Crossover check: R3 consistency ────────────
            # R3 is the shared node. Its output from bottom loop XOR
            # its top-loop input should NOT be zero.
            r3_crossover = bytes(
                a ^ b for a, b in zip(bottom_r3_out, top_input)
            )
            if r3_crossover == null:
                return False  # R3 is degenerate

            # ── Figure-8 token: R2 (hub) binds both loops ──
            figure8_token = hashlib.sha256(
                bottom_r3_out + r2 + top_r1_out
            ).digest()
            if figure8_token == null:
                return False

            # ── Entropy gates ───────────────────────────────
            e_cross = sum(bin(b).count('1') for b in r3_crossover)
            e_figure = sum(bin(b).count('1') for b in figure8_token)
            e_bottom = sum(bin(b).count('1') for b in bottom_r3_out)
            e_top = sum(bin(b).count('1') for b in top_r1_out)

            min_entropy = 80 if in_grace else 96

            if e_cross < min_entropy:
                return False
            if e_figure < min_entropy:
                return False
            if e_bottom < 64:
                return False
            if e_top < 64:
                return False

            return True

        except Exception:
            return False


# ── SCORING ──






class HealthScorer:
    """Scores 8CV health and determines buzzkill escalation."""

    STATUS_SCORES = {
        LoopStatus.HEALTHY: 25,
        LoopStatus.DEGRADED: 15,
        LoopStatus.CRITICAL: 5,
        LoopStatus.FAILED: 0,
    }

    def score(self, cycle_id: str, top_status: LoopStatus,
              bottom_status: LoopStatus, cross_valid: bool,
              cycle_count: int) -> LoopHealthReport:
        """
        FIXED scoring:
        - Grace period: cross-val fail = warning only, never buzzkill
        - Both loops HEALTHY + cross-val fail = timing anomaly (T1)
        - Both loops FAILED + cross-val fail = real compromise (T3)
        - Partial = T2
        """
        top_score = self.STATUS_SCORES[top_status]
        bottom_score = self.STATUS_SCORES[bottom_status]
        trigger = None
        details = []
        in_grace = cycle_count <= GRACE_CYCLES

        if not cross_valid:
            if in_grace:
                details.append(
                    f"Cross-val warming up "
                    f"(cycle {cycle_count}/{GRACE_CYCLES})"
                )
                top_score = min(top_score, 20)
                bottom_score = min(bottom_score, 20)
            else:
                both_healthy = (
                    top_status == LoopStatus.HEALTHY and
                    bottom_status == LoopStatus.HEALTHY
                )
                both_compromised = (
                    top_status in (LoopStatus.FAILED, LoopStatus.CRITICAL) and
                    bottom_status in (LoopStatus.FAILED, LoopStatus.CRITICAL)
                )

                if both_healthy:
                    # Loops fine — key timing anomaly at crossover
                    trigger = BuzzkillTier.TIER_1_SURGICAL
                    top_score = min(top_score, 18)
                    bottom_score = min(bottom_score, 18)
                    details.append(
                        "Cross-val mismatch — 8CV timing anomaly. "
                        "Loops healthy. Surgical buzzkill."
                    )
                elif both_compromised:
                    # Real breach — both loops AND cross-val failed
                    trigger = BuzzkillTier.TIER_3_LIVE_BURN
                    top_score = 0
                    bottom_score = 0
                    details.append(
                        "CRITICAL: Cross-val failed + both loops down. "
                        "Hub (R2 EvoFuse) or shared node (R3 PassPatrol) compromised."
                    )
                else:
                    # Partial — one loop degraded + cross-val failed
                    trigger = BuzzkillTier.TIER_2_SCORCHED
                    top_score = min(top_score, 10)
                    bottom_score = min(bottom_score, 10)
                    details.append(
                        "Cross-val failed + partial loop failure. "
                        "Scorched buzzkill."
                    )

        # Single loop failure even if cross-val passed
        if top_status == LoopStatus.FAILED and not in_grace:
            if trigger is None:
                trigger = BuzzkillTier.TIER_2_SCORCHED
            details.append("TOP loop FAILED")

        if bottom_status == LoopStatus.FAILED and not in_grace:
            if trigger is None:
                trigger = BuzzkillTier.TIER_2_SCORCHED
            details.append("BOTTOM loop FAILED")

        total = top_score + bottom_score

        # Last resort: score collapse
        if total <= 10 and not in_grace and trigger is None:
            trigger = BuzzkillTier.TIER_1_SURGICAL
            details.append(f"Score collapse: {total}/50")

        return LoopHealthReport(
            timestamp=time.time(),
            cycle_id=cycle_id,
            health_score=total,
            top_loop=top_status,
            bottom_loop=bottom_status,
            buzzkill_trigger=trigger,
            failure_details=" | ".join(details),
        )


# ── BUZZKILL ──





class BuzzkillEngine:
    """FC_FLOW custom sigkill — surgical to live burn escalation."""

    _log = logging.getLogger("Buzzkill")

    def __init__(self, feed, commander):
        self._feed = feed
        self._commander = commander
        self._buzzkill_cb = None

    def set_callback(self, cb):
        self._buzzkill_cb = cb

    def fire(self, tier: BuzzkillTier, reason: str, engine=None):
        """Execute buzzkill at specified tier."""
        write_audit("BUZZKILL", f"Tier {tier.value} ({tier.name}): {reason}")
        self._feed.push(
            "BUZZKILL",
            {"tier": tier.value, "name": tier.name, "reason": reason},
            priority="CRITICAL",
        )
        self._commander.alert(
            f"BUZZKILL_TIER_{tier.value}", reason, "CRITICAL"
        )

        if self._buzzkill_cb:
            try:
                self._buzzkill_cb(tier, reason)
            except Exception as e:
                self._log.error(f"Buzzkill callback error: {e}")

        if tier == BuzzkillTier.TIER_3_LIVE_BURN:
            LiveBurn.execute(engine, reason)


class LiveBurn:
    """Final escalation — live burn all key material."""

    _log = logging.getLogger("LiveBurn")

    @classmethod
    def execute(cls, engine, reason: str):
        cls._log.critical("╔══════════════════════════════════════╗")
        cls._log.critical("║        LIVE BURN EXECUTING           ║")
        cls._log.critical(f"║ {reason[:38]:<38} ║")
        cls._log.critical("╚══════════════════════════════════════╝")

        write_audit("LIVE_BURN", reason)
        try:
            if engine:
                engine.wipe_keys()
        except Exception:
            pass

        cls._log.critical(
            f"[LIVE BURN] All key material destroyed. "
            f"Process terminating. Reason: {reason}"
        )
        os._exit(0)


# ── FIGURE8 ENGINE ──






class Figure8Engine:
    """
    8CV (8-Core-Velocity) Engine — FC_FLOW figure-8 loop orchestrator.
    Manages key rotation, loop validation, crossover checks, and buzzkill.
    """

    def __init__(self, token_feed, commander):
        self._feed = token_feed
        self._commander = commander
        self._gear = GearState.GEAR_2_ACTIVE
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # 8CV subsystems
        self._keys = KeyStore()
        self._loops = LoopValidator(self._keys)
        self._crossover = CrossoverValidator(self._keys)
        self._scorer = HealthScorer()
        self._buzzkill = BuzzkillEngine(token_feed, commander)

        # State
        self._health_history: List[LoopHealthReport] = []
        self._last_report: Optional[LoopHealthReport] = None
        self._consecutive_fails = 0
        self._replay_window: List[str] = []
        self._cycle_count = 0
        self._log = logging.getLogger("8CV")

        # Callbacks
        self._gear_shift_cb: Optional[Callable] = None

    # ── Public API ────────────────────────────────────────
    def start(self, gear: GearState = GearState.GEAR_2_ACTIVE):
        if self._running:
            return
        self._gear = gear
        self._running = True
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="8CV-Engine"
        )
        self._thread.start()
        write_audit("ENGINE_START", f"Gear={gear.name}")
        self._feed.push("ENGINE_START", {"gear": gear.name}, priority="CRITICAL")
        self._commander.alert("ENGINE_START", gear.name, "INFO")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        self._keys.wipe_all()
        write_audit("ENGINE_STOP", "All key material burned")
        self._feed.push("ENGINE_STOP", {"burned": True}, priority="CRITICAL")
        self._commander.alert("ENGINE_STOP", "Key material burned", "WARNING")

    def shift_gear(self, target: GearState, reason: str):
        with self._lock:
            old = self._gear
            self._gear = target
        write_audit("GEAR_SHIFT", f"{old.name} → {target.name} | {reason}")
        self._feed.push(
            "GEAR_SHIFT",
            {"from": old.name, "to": target.name, "reason": reason},
            priority="CRITICAL",
        )
        self._commander.alert(
            "GEAR_SHIFT",
            f"{old.name} → {target.name}: {reason}",
            "WARNING" if target == GearState.GEAR_3_UNDISPUTED else "INFO",
        )

    def get_gear(self) -> GearState:
        return self._gear

    def get_health_report(self) -> Optional[LoopHealthReport]:
        return self._last_report

    def get_health_history(self) -> List[LoopHealthReport]:
        return list(self._health_history)

    def get_cycle_count(self) -> int:
        return self._cycle_count

    def set_gear_shift_callback(self, cb: Callable):
        self._gear_shift_cb = cb

    def wipe_keys(self):
        """Burn all keys — called by LiveBurn."""
        self._keys.wipe_all()

    # ── Main 8CV loop ─────────────────────────────────────
    def _run(self):
        while self._running:
            start = time.monotonic()
            try:
                self._cycle()
            except Exception as e:
                self._log.error(f"8CV cycle error: {e}")
                self._consecutive_fails += 1

            override = self._commander.consume_override()
            if override:
                self._apply_override(override)

            if self._gear != GearState.GEAR_3_UNDISPUTED:
                elapsed = time.monotonic() - start
                time.sleep(max(0.0, CYCLE_INTERVAL - elapsed))

    def _cycle(self):
        self._cycle_count += 1
        cycle_id = self._make_cycle_id()

        # Replay protection
        if cycle_id in self._replay_window:
            self._buzzkill.fire(
                BuzzkillTier.TIER_2_SCORCHED,
                f"Replay attack: {cycle_id[:16]}",
                engine=self
            )
            return

        self._replay_window.append(cycle_id)
        if len(self._replay_window) > REPLAY_WINDOW:
            self._replay_window.pop(0)

        # Rotate keys
        self._keys.rotate()

        # 8CV topology validation
        top_status = self._loops.validate_top()
        bottom_status = self._loops.validate_bottom()
        cross_valid = self._crossover.validate(self._cycle_count)

        # Score health
        report = self._scorer.score(
            cycle_id, top_status, bottom_status,
            cross_valid, self._cycle_count
        )
        self._process_health_report(report)

        # Burn keys after validation (not replay window)
        self._keys.wipe_all()

        # Feed cycle event
        self._feed.push(
            "CYCLE",
            {
                "cycle": self._cycle_count,
                "gear": self._gear.name,
                "health": report.health_score,
                "top": report.top_loop.value,
                "bottom": report.bottom_loop.value,
                "cross": cross_valid,
                "cycle_id": cycle_id[:16],
            },
        )

    def _make_cycle_id(self) -> str:
        data = (
            self._cycle_count.to_bytes(8, "big") +
            self._gear.value.to_bytes(1, "big") +
            str(time.monotonic()).encode() +
            b"".join(self._keys.get(r).split for r in sorted(self._keys.all_splits()))
        )
        return hashlib.sha256(data).hexdigest()

    def _process_health_report(self, report: LoopHealthReport):
        self._last_report = report
        self._health_history.append(report)
        if len(self._health_history) > HEALTH_HISTORY:
            self._health_history.pop(0)

        if report.health_score < 50:
            self._consecutive_fails += 1
        else:
            self._consecutive_fails = 0

        if report.buzzkill_trigger is not None:
            self._buzzkill.fire(
                report.buzzkill_trigger,
                (
                    f"Health failure. Score={report.health_score}/50. "
                    f"Top={report.top_loop.value}. "
                    f"Bottom={report.bottom_loop.value}. "
                    f"{report.failure_details}"
                ),
                engine=self
            )

        self._evaluate_escalation(report)
        self._evaluate_deescalation(report)

    def _evaluate_escalation(self, report: LoopHealthReport):
        if self._gear == GearState.GEAR_3_UNDISPUTED:
            return
        reason = None
        if report.health_score <= 24:
            reason = f"CRITICAL score: {report.health_score}/50"
        elif report.health_score <= 49:
            reason = f"WARNING score: {report.health_score}/50"
        elif self._consecutive_fails >= 3:
            reason = f"Consecutive failures: {self._consecutive_fails}"
        if reason:
            self.shift_gear(GearState.GEAR_3_UNDISPUTED, reason)
            if report.health_score <= 24:
                self._commander.alert("CRITICAL_HEALTH", reason, "CRITICAL")

    def _evaluate_deescalation(self, report: LoopHealthReport):
        if self._gear != GearState.GEAR_3_UNDISPUTED:
            return
        if report.health_score < 50 or self._consecutive_fails > 0:
            return
        healthy_run = sum(
            1 for r in reversed(self._health_history)
            if r.health_score == 50
        )
        if healthy_run >= HEALTHY_CYCLES:
            self.shift_gear(
                GearState.GEAR_2_ACTIVE,
                f"Threat cleared. {healthy_run} healthy cycles.",
            )

    def _apply_override(self, override: dict):
        cmd = override.get("command")
        params = override.get("params", {})
        if cmd == "GEAR_SHIFT":
            target = GearState[params.get("target", "GEAR_2_ACTIVE")]
            self.shift_gear(target, "Commander override")
        elif cmd == "BUZZKILL":
            tier = BuzzkillTier[params.get("tier", "TIER_1_SURGICAL")]
            self._buzzkill.fire(tier, "Commander manual buzzkill", engine=self)
        elif cmd == "LIVE_BURN":
            LiveBurn.execute(self, "Commander manual LIVE BURN")
        write_audit("OVERRIDE_APPLIED", f"{cmd}: {params}")


# ── TOKEN FEED ──





class TokenFeed:
    """Undisputed token feed — distributes events to AI team."""

    _lock = threading.Lock()

    def __init__(self):
        os.makedirs(FEEDS_DIR, exist_ok=True)
        for ai in AI_TEAM:
            self._ensure_feed(ai)

    def _ensure_feed(self, ai_name: str):
        path = os.path.join(FEEDS_DIR, f"{ai_name}.json")
        if not os.path.exists(path):
            with open(path, 'w') as f:
                json.dump({"agent": ai_name, "events": []}, f, indent=2)

    def push(self, event: str, payload: dict,
             targets: Optional[List[str]] = None,
             priority: str = "NORMAL"):
        token = {
            "ts": datetime.now().isoformat(),
            "event": event,
            "payload": payload,
        }
        agents = targets if targets else list(AI_TEAM.keys())

        with self._lock:
            for ai in agents:
                self._ensure_feed(ai)
                path = os.path.join(FEEDS_DIR, f"{ai}.json")
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                    data["events"].append(token)
                    if len(data["events"]) > MAX_FEED_EVENTS:
                        data["events"] = data["events"][-MAX_FEED_EVENTS:]
                    with open(path, 'w') as f:
                        json.dump(data, f, indent=2)
                except Exception as e:
                    logging.getLogger("TokenFeed").warning(f"Push failed for {ai}: {e}")

    def read_feed(self, ai_name: str, last_n: int = 10) -> List[dict]:
        path = os.path.join(FEEDS_DIR, f"{ai_name}.json")
        if not os.path.exists(path):
            return []
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            return data["events"][-last_n:]
        except Exception:
            return []

    def clear_feed(self, ai_name: str):
        path = os.path.join(FEEDS_DIR, f"{ai_name}.json")
        with open(path, 'w') as f:
            json.dump({"agent": ai_name, "events": []}, f, indent=2)


# ── COMMANDER ──





class Commander:
    """FC_FLOW Commander — issues alerts and overrides for 8CV."""

    def __init__(self, token_feed):
        self._feed = token_feed
        self._alerts: List[CommanderAlert] = []
        self._lock = threading.Lock()
        self._override: Optional[dict] = None

    def alert(self, event: str, detail: str, severity: str = "INFO"):
        a = CommanderAlert(
            timestamp=datetime.now().isoformat(),
            event=event,
            detail=detail,
            severity=severity,
        )
        with self._lock:
            self._alerts.append(a)
            if len(self._alerts) > 200:
                self._alerts = self._alerts[-200:]

        self._feed.push(
            event=f"COMMANDER_{event}",
            payload={"detail": detail, "severity": severity},
            priority="CRITICAL" if severity == "CRITICAL" else "NORMAL",
        )

        try:
            os.makedirs(SHARED_DIR, exist_ok=True)
            with open(COMMANDER_LOG, 'a') as f:
                f.write(f"{a.timestamp} [{severity}] {event}: {detail}\n")
        except Exception:
            pass

    def get_alerts(self, last_n: int = 20) -> List[CommanderAlert]:
        with self._lock:
            return self._alerts[-last_n:]

    def clear_alerts(self):
        with self._lock:
            self._alerts.clear()

    def issue_override(self, command: str, params: dict):
        with self._lock:
            self._override = {"command": command, "params": params}
        self.alert(
            event="OVERRIDE_ISSUED",
            detail=f"{command}: {params}",
            severity="WARNING",
        )

    def consume_override(self) -> Optional[dict]:
        with self._lock:
            ov = self._override
            self._override = None
            return ov


# ── REACTIVE OPTIMIZER ──





class ReactiveOptimizer:
    """
    8CV Reactive Optimizer.
    Stabilizes token push rate + detects mistake patterns.
    Prevents connection burnout when AI queries are live.
    """
    THROTTLE_RATE = 5.0
    IDLE_RATE = 0.5
    SURGE_RATE = 10.0
    BATCH_WINDOW = 2.0
    MAX_CONNS = 4

    CRITICAL_EVENTS = {
        "BUZZKILL", "LIVE_BURN", "GEAR_SHIFT",
        "ENGINE_STOP", "ENGINE_START",
        "COMMANDER_CRITICAL_HEALTH",
        "OPTIMIZER_ALERT", "OPTIMIZER_MODE_CHANGE",
    }

    def __init__(self, feed, engine):
        self._feed = feed
        self._engine = engine
        self._state = OptimizerState()
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._token_ts: List[float] = []
        self._batch_buffer: List[dict] = []
        self._last_flush = 0.0
        self._patterns: List[dict] = []
        self._active_conns = 0
        self._log = logging.getLogger("8CV-Optimizer")

    def start(self):
        self._running = True
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="8CV-Optimizer"
        )
        self._thread.start()
        write_audit("OPTIMIZER_START", "8CV reactive optimizer online")

    def stop(self):
        self._running = False

    def get_state(self) -> OptimizerState:
        with self._lock:
            return self._state

    def should_push(self, event: str, priority: str = "NORMAL") -> bool:
        if event in self.CRITICAL_EVENTS or priority == "CRITICAL":
            return True
        mode = self._state.mode
        if mode == OptimizerMode.SURGE:
            return False
        if mode == OptimizerMode.IDLE:
            return event in {"CYCLE", "ENGINE_START"}
        if mode == OptimizerMode.THROTTLE:
            self._buffer_event(event)
            return False
        return True

    def record_push(self):
        with self._lock:
            now = time.monotonic()
            self._token_ts.append(now)
            cutoff = now - 10.0
            self._token_ts = [t for t in self._token_ts if t > cutoff]

    def record_conn(self, delta: int):
        with self._lock:
            self._active_conns = max(0, self._active_conns + delta)

    def record_pattern(self, event: str, context: dict):
        with self._lock:
            self._patterns.append({
                "ts": time.monotonic(),
                "event": event,
                "context": context,
            })
            if len(self._patterns) > 100:
                self._patterns = self._patterns[-100:]
        self._analyze()

    def flush_batch(self) -> List[dict]:
        with self._lock:
            batch = list(self._batch_buffer)
            self._batch_buffer = []
            self._last_flush = time.monotonic()
        return batch

    def _analyze(self):
        with self._lock:
            recent = list(self._patterns[-20:])
        buzzkills = [p for p in recent if p["event"] == "BUZZKILL"]
        if len(buzzkills) >= 3:
            tiers = [p["context"].get("tier") for p in buzzkills]
            if len(set(tiers)) == 1:
                self._feed.push(
                    "OPTIMIZER_ALERT",
                    {
                        "pattern": "REPEATED_BUZZKILL",
                        "tier": tiers[0],
                        "count": len(buzzkills),
                        "advice": (
                            "Buzzkill Tier {} firing {}x. "
                            "Check R3 PassPatrol integrity. "
                            "Consider Gear 1 Standby to let keys stabilize."
                        ).format(tiers[0], len(buzzkills)),
                    },
                    priority="CRITICAL",
                )
                write_audit(
                    "OPTIMIZER_PATTERN",
                    f"Repeated Buzzkill Tier {tiers[0]}: {len(buzzkills)}x",
                )

    def _run(self):
        while self._running:
            self._update_state()
            self._flush_if_due()
            self._suggest_deescalation()
            time.sleep(1.0)

    def _update_state(self):
        with self._lock:
            now = time.monotonic()
            cutoff = now - 10.0
            recent_count = sum(1 for t in self._token_ts if t > cutoff)
            rate = recent_count / 10.0
            conns = self._active_conns

        gear = self._engine.get_gear()
        pressure = {
            GearState.GEAR_1_STANDBY: 0.2,
            GearState.GEAR_2_ACTIVE: 0.5,
            GearState.GEAR_3_UNDISPUTED: 1.0,
        }.get(gear, 0.5)

        if rate >= self.SURGE_RATE or pressure >= 1.0:
            mode = OptimizerMode.SURGE
        elif rate >= self.THROTTLE_RATE or conns >= self.MAX_CONNS:
            mode = OptimizerMode.THROTTLE
        elif rate <= self.IDLE_RATE and pressure <= 0.2:
            mode = OptimizerMode.IDLE
        else:
            mode = OptimizerMode.NORMAL

        old_mode = self._state.mode
        with self._lock:
            batch_count = len(self._batch_buffer)
            self._state = OptimizerState(
                token_rate=rate,
                connection_load=conns,
                cycle_pressure=pressure,
                mode=mode,
                batch_count=batch_count,
            )

        if mode != old_mode:
            self._log.info(f"Optimizer: {old_mode.value} → {mode.value}")
            write_audit(
                "OPTIMIZER_MODE",
                f"{old_mode.value} → {mode.value} | rate={rate:.1f}/s pressure={pressure:.1f}",
            )
            self._feed.push(
                "OPTIMIZER_MODE_CHANGE",
                {
                    "from": old_mode.value,
                    "to": mode.value,
                    "rate": round(rate, 2),
                    "pressure": round(pressure, 2),
                },
                priority="CRITICAL",
            )

    def _flush_if_due(self):
        now = time.monotonic()
        if (self._state.mode == OptimizerMode.THROTTLE and
                now - self._last_flush >= self.BATCH_WINDOW):
            batch = self.flush_batch()
            if batch:
                self._feed.push(
                    "OPTIMIZER_BATCH_FLUSH",
                    {
                        "count": len(batch),
                        "events": [b["event"] for b in batch],
                    },
                )
                write_audit("OPTIMIZER_FLUSH", f"Flushed {len(batch)} events")

    def _suggest_deescalation(self):
        report = self._engine.get_health_report()
        if not report:
            return
        if (self._state.mode == OptimizerMode.SURGE and
                self._engine.get_gear() == GearState.GEAR_3_UNDISPUTED and
                report.health_score == 50 and
                self._engine.get_cycle_count() > GRACE_CYCLES + 20):
            self._feed.push(
                "OPTIMIZER_SUGGESTION",
                {
                    "suggestion": "CONSIDER_DEESCALATION",
                    "reason": (
                        "Engine in Gear 3 + SURGE mode but "
                        "health is 50/50. May be over-reacting. "
                        "Consider manual shift to Gear 2."
                    ),
                },
                priority="CRITICAL",
            )

    def _buffer_event(self, event: str):
        with self._lock:
            self._batch_buffer.append({
                "event": event,
                "ts": time.monotonic(),
            })


# ── WEB STATE ──






class WebState:
    """Builds clean JSON snapshot of full 8CV mesh for web clients."""

    def __init__(self, engine, commander, feed, optimizer):
        self._engine = engine
        self._commander = commander
        self._feed = feed
        self._optimizer = optimizer

    def snapshot(self) -> dict:
        engine = self._engine
        commander = self._commander
        opt = self._optimizer
        report = engine.get_health_report()
        history = engine.get_health_history()
        alerts = commander.get_alerts(last_n=10)
        opt_state = opt.get_state()

        rooms_data = {}
        for room_id, label in ROOMS.items():
            status = "HEALTHY"
            rooms_data[room_id] = {
                "label": label,
                "status": status,
                "locked": status == "LOCKED",
            }

        chart = [
            {
                "score": r.health_score,
                "top": r.top_loop.value,
                "bottom": r.bottom_loop.value,
                "ts": r.timestamp,
            }
            for r in history
        ]

        feeds_data = {}
        for ai in AI_TEAM:
            feeds_data[ai] = self._feed.read_feed(ai, last_n=5)

        return {
            "ts": datetime.now().isoformat(),
            "version": VERSION,
            "engine": {
                "gear": engine.get_gear().name,
                "gear_num": engine.get_gear().value,
                "cycles": engine.get_cycle_count(),
                "health": report.health_score if report else 0,
                "top_loop": report.top_loop.value if report else "UNKNOWN",
                "bottom_loop": report.bottom_loop.value if report else "UNKNOWN",
                "consecutive_fails": getattr(engine, '_consecutive_fails', 0),
                "in_grace": engine.get_cycle_count() <= GRACE_CYCLES,
            },
            "optimizer": {
                "mode": opt_state.mode.value,
                "token_rate": round(opt_state.token_rate, 2),
                "connections": opt_state.connection_load,
                "pressure": round(opt_state.cycle_pressure, 2),
                "batch_count": opt_state.batch_count,
            },
            "rooms": rooms_data,
            "chart": chart,
            "alerts": [
                {
                    "ts": a.timestamp,
                    "event": a.event,
                    "detail": a.detail,
                    "severity": a.severity,
                }
                for a in alerts
            ],
            "feeds": feeds_data,
            "roster": {"agents": AI_TEAM},
            "turf": {"status": "STABLE"},
            "logic": True,
        }


# ── WEBSOCKET SERVER ──





class WSClient:
    """One connected browser tab."""

    def __init__(self, conn: socket.socket, addr):
        self.conn = conn
        self.addr = addr
        self.alive = True
        self._lock = threading.Lock()

    def send_text(self, text: str):
        if not self.alive:
            return
        try:
            data = text.encode('utf-8')
            length = len(data)
            with self._lock:
                if length <= 125:
                    header = bytes([0x81, length])
                elif length <= 65535:
                    header = struct.pack('>BBH', 0x81, 126, length)
                else:
                    header = struct.pack('>BBQ', 0x81, 127, length)
                self.conn.sendall(header + data)
        except Exception:
            self.alive = False

    def close(self):
        self.alive = False
        try:
            self.conn.close()
        except Exception:
            pass


class WSServer:
    """Minimal WebSocket server — stdlib only, no dependencies."""

    WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    def __init__(self, web_state, host: str = WEB_HOST, port: int = WS_PORT):
        self._web_state = web_state
        self._host = host
        self._port = port
        self._clients: list = []
        self._lock = threading.Lock()
        self._running = False
        self._log = logging.getLogger("FC_FLOW-WS")
        self._optimizer = None

    def start(self):
        self._running = True
        threading.Thread(target=self._accept_loop, daemon=True, name="WS-Accept").start()
        threading.Thread(target=self._broadcast_loop, daemon=True, name="WS-Broadcast").start()

    def set_optimizer(self, optimizer):
        self._optimizer = optimizer

    def _accept_loop(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            srv.bind((self._host, self._port))
            srv.listen(MAX_WS_CLIENTS)
            srv.settimeout(1.0)
            self._log.info(f"WebSocket listening on {self._host}:{self._port}")
            while self._running:
                try:
                    conn, addr = srv.accept()
                    threading.Thread(target=self._handshake, args=(conn, addr), daemon=True).start()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self._running:
                        self._log.warning(f"Accept error: {e}")
                    break
        finally:
            try:
                srv.close()
            except Exception:
                pass

    def _handshake(self, conn: socket.socket, addr):
        try:
            conn.settimeout(5.0)
            data = conn.recv(4096).decode('utf-8', errors='replace')
            if not data:
                conn.close()
                return
            lines = data.split('\r\n')
            headers = {}
            for line in lines[1:]:
                if ': ' in line:
                    k, v = line.split(': ', 1)
                    headers[k] = v
            key = headers.get('Sec-WebSocket-Key', '')
            accept = base64.b64encode(
                hashlib.sha1((key + self.WS_MAGIC).encode()).digest()
            ).decode()
            response = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {accept}\r\n"
                "\r\n"
            )
            conn.sendall(response.encode())
            client = WSClient(conn, addr)
            with self._lock:
                self._clients.append(client)
                if self._optimizer:
                    self._optimizer.record_conn(+1)
            self._log.info(f"WS client connected: {addr}")
            write_audit("WS_CONNECT", str(addr))
            self._read_loop(client)
        except Exception as e:
            self._log.warning(f"Handshake failed {addr}: {e}")
            try:
                conn.close()
            except Exception:
                pass

    def _read_loop(self, client: WSClient):
        client.conn.settimeout(30.0)
        while client.alive and self._running:
            try:
                header = self._recv_exact(client.conn, 2)
                if not header:
                    break
                fin_opcode = header[0]
                mask_len = header[1]
                opcode = fin_opcode & 0x0F
                masked = bool(mask_len & 0x80)
                length = mask_len & 0x7F
                if length == 126:
                    ext = self._recv_exact(client.conn, 2)
                    if not ext:
                        break
                    length = struct.unpack('>H', ext)[0]
                elif length == 127:
                    ext = self._recv_exact(client.conn, 8)
                    if not ext:
                        break
                    length = struct.unpack('>Q', ext)[0]
                mask_key = b''
                if masked:
                    mask_key = self._recv_exact(client.conn, 4)
                    if not mask_key:
                        break
                payload = self._recv_exact(client.conn, length)
                if not payload:
                    break
                if masked and mask_key:
                    payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
                if opcode == 0x8:
                    break
                elif opcode == 0x9:
                    try:
                        client.conn.sendall(bytes([0x8A, 0x00]))
                    except Exception:
                        break
            except socket.timeout:
                try:
                    client.conn.sendall(bytes([0x89, 0x00]))
                except Exception:
                    break
            except Exception:
                break
        client.alive = False
        try:
            with self._lock:
                self._clients = [c for c in self._clients if c.alive]
            if self._optimizer:
                self._optimizer.record_conn(-1)
            write_audit("WS_DISCONNECT", str(client.addr))
        except Exception:
            pass

    def _recv_exact(self, conn: socket.socket, n: int) -> bytes:
        buf = b''
        while len(buf) < n:
            try:
                chunk = conn.recv(n - len(buf))
                if not chunk:
                    return b''
                buf += chunk
            except (socket.error, ConnectionError):
                return b''
            except Exception:
                return b''
        return buf

    def _broadcast_loop(self):
        interval = 1.0 / WS_BROADCAST_HZ
        while self._running:
            start = time.monotonic()
            try:
                snapshot = self._web_state.snapshot()
                payload = json.dumps(snapshot)
                with self._lock:
                    clients = list(self._clients)
                for client in clients:
                    if client.alive:
                        try:
                            client.send_text(payload)
                        except Exception:
                            client.alive = False
                with self._lock:
                    self._clients = [c for c in self._clients if c.alive]
            except Exception as e:
                self._log.warning(f"Broadcast error: {e}")
                time.sleep(0.1)
            elapsed = time.monotonic() - start
            time.sleep(max(0.0, interval - elapsed))


# ── HTTP SERVER ──





class MeshHTTPHandler(BaseHTTPRequestHandler):
    """Serves Web Command Center + handles API commands."""

    web_state = None
    commander = None
    engine = None
    feed = None

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == '/':
            self._serve_html()
        elif path == '/state':
            self._serve_state()
        elif path == '/audit':
            self._serve_audit()
        elif path == '/commander_log':
            self._serve_commander_log()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == '/command':
            self._handle_command()
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def _cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _serve_html(self):
        html = build_html()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(html.encode())))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(html.encode())

    def _serve_state(self):
        data = json.dumps(self.web_state.snapshot()).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(data)

    def _serve_audit(self):
        lines = []
        if os.path.exists(AUDIT_LOG):
            with open(AUDIT_LOG, 'r') as f:
                lines = f.readlines()[-50:]
        data = json.dumps({"lines": [l.rstrip() for l in lines]}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(data)

    def _serve_commander_log(self):
        lines = []
        if os.path.exists(COMMANDER_LOG):
            with open(COMMANDER_LOG, 'r') as f:
                lines = f.readlines()[-50:]
        data = json.dumps({"lines": [l.rstrip() for l in lines]}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(data)

    def _handle_command(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            if length <= 0:
                self._json_response({"ok": False, "error": "No request body"}, 400)
                return
            body = self.rfile.read(length)
            payload = json.loads(body.decode())
            cmd = payload.get('command', '')
            params = payload.get('params', {})
            valid = {
                'GEAR_SHIFT', 'BUZZKILL', 'LIVE_BURN',
                'FLEX_LOCKDOWN', 'FLEX_UNLOCK',
                'CLEAR_ALERTS', 'SCAFFOLD',
            }
            if cmd not in valid:
                self._json_response({"ok": False, "error": f"Unknown command: {cmd}"}, 400)
                return
            self.commander.issue_override(cmd, params)
            self._json_response({"ok": True})
        except Exception as e:
            self._json_response({"ok": False, "error": str(e)}, 500)

    def _json_response(self, data: dict, status: int = 200):
        data_str = json.dumps(data)
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data_str)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(data_str.encode())


# ── HTML BUILDER ──




def build_html() -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>FlowStation — FC_FLOW Command Center</title>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: 'Courier New', monospace;
            background-color: #000;
            color: #0f0;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            color: #0f0;
            text-shadow: 0 0 10px #0f0;
        }}
        .panel {{
            background-color: #111;
            border: 1px solid #0f0;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
        }}
        .status {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-weight: bold;
            margin: 2px;
        }}
        .healthy {{ background-color: #003300; color: #0f0; }}
        .degraded {{ background-color: #333300; color: #ff0; }}
        .critical {{ background-color: #330000; color: #f00; }}
        .failed {{ background-color: #660000; color: #f00; }}
        .locked {{ background-color: #000033; color: #00f; }}
        .button {{
            background-color: #003300;
            color: #0f0;
            border: 1px solid #0f0;
            padding: 8px 15px;
            margin: 5px;
            cursor: pointer;
            font-family: 'Courier New', monospace;
        }}
        .button:hover {{ background-color: #005500; }}
        .button.burn {{
            background-color: #330000;
            border-color: #f00;
            color: #f00;
        }}
        .button.burn:hover {{ background-color: #550000; }}
        .chart {{
            height: 200px;
            border: 1px solid #0f0;
            margin: 10px 0;
            position: relative;
            overflow: hidden;
        }}
        .bar {{
            position: absolute;
            bottom: 0;
            width: 4px;
            background-color: #0f0;
        }}
        .log {{
            background-color: #001100;
            border: 1px solid #0f0;
            padding: 10px;
            height: 150px;
            overflow-y: auto;
            font-size: 12px;
        }}
        .command-panel {{
            display: flex;
            flex-wrap: wrap;
        }}
        .command-button {{
            margin: 5px;
            flex: 1 1 150px;
        }}
        .room-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
        }}
        .room-card {{
            border: 1px solid #0f0;
            padding: 10px;
            text-align: center;
        }}
        .room-name {{
            font-weight: bold;
            font-size: 14px;
        }}
        .room-role {{
            font-size: 11px;
            color: #888;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>⚡ FlowStation — FC_FLOW Command Center</h1>
        <div style="color: #888; margin-bottom: 20px;">
            Sovereign Fuel Mesh | 8CV (8-Core-Velocity) v{VERSION}
        </div>

        <div id="status" class="panel">
            <h2>8CV Core Status</h2>
            <div id="engine-status">Loading...</div>
            <div id="optimizer-status">Loading...</div>
        </div>

        <div id="rooms" class="panel">
            <h2>Room Status — Sovereign Fuel Mesh</h2>
            <div class="room-grid" id="rooms-grid">Loading...</div>
        </div>

        <div id="health" class="panel">
            <h2>8CV Health Chart</h2>
            <div id="health-chart" class="chart"></div>
        </div>

        <div id="alerts" class="panel">
            <h2>Alerts <span id="alert-count">(0)</span></h2>
            <div id="alerts-content" class="log"></div>
        </div>

        <div class="panel">
            <h2>FC_FLOW Command Center</h2>
            <div id="command-buttons" class="command-panel">
                <button class="button command-button" onclick="sendCommand('GEAR_SHIFT', {{'target': 'GEAR_1_STANDBY'}})">Gear 1 Standby</button>
                <button class="button command-button" onclick="sendCommand('GEAR_SHIFT', {{'target': 'GEAR_2_ACTIVE'}})">Gear 2 Active</button>
                <button class="button command-button" onclick="sendCommand('GEAR_SHIFT', {{'target': 'GEAR_3_UNDISPUTED'}})">Gear 3 UnDisputed</button>
                <button class="button command-button" onclick="sendCommand('BUZZKILL', {{'tier': 'TIER_1_SURGICAL'}})">Buzzkill T1</button>
                <button class="button command-button" onclick="sendCommand('BUZZKILL', {{'tier': 'TIER_2_SCORCHED'}})">Buzzkill T2</button>
                <button class="button command-button" onclick="sendCommand('BUZZKILL', {{'tier': 'TIER_3_LIVE_BURN'}})">Buzzkill T3</button>
                <button class="button command-button burn" onclick="sendCommand('LIVE_BURN', {{}})">🔥 LIVE BURN</button>
                <button class="button command-button" onclick="sendCommand('CLEAR_ALERTS', {{}})">Clear Alerts</button>
            </div>
        </div>

        <div id="ai-feeds" class="panel">
            <h2>AI Feeds — Undisputed Tokens</h2>
            <div id="ai-feeds-content">Loading...</div>
        </div>
    </div>

    <script>
        const WS_URL = 'ws://localhost:{WS_PORT}';
        let ws = null;
        let state = {{}};

        const ROOM_ROLES = {{
            'room_0': 'Sovereign Fuel — Power',
            'room_1': 'Logic Lock — Auth',
            'room_2': 'EvoFuse — HUB',
            'room_3': 'PassPatrol — Crossover',
            'room_4': 'FlowControl — Bottom',
            'room_5': 'AiZquad — Bottom'
        }};

        function connectWebSocket() {{
            try {{
                ws = new WebSocket(WS_URL);
                ws.onopen = function() {{
                    console.log("FC_FLOW WebSocket connected");
                }};
                ws.onmessage = function(event) {{
                    try {{
                        const data = JSON.parse(event.data);
                        updateUI(data);
                    }} catch (e) {{
                        console.error("Parse error:", e);
                    }}
                }};
                ws.onclose = function() {{
                    console.log("FC_FLOW WebSocket closed — reconnecting...");
                    setTimeout(connectWebSocket, 1000);
                }};
                ws.onerror = function(error) {{
                    console.error("WebSocket error:", error);
                }};
            }} catch (error) {{
                setTimeout(connectWebSocket, 1000);
            }}
        }}

        function updateUI(data) {{
            state = data;
            const engine = data.engine || {{}};
            const optimizer = data.optimizer || {{}};

            // Engine status
            const gearClass = engine.gear === 'GEAR_3_UNDISPUTED' ? 'critical' :
                             engine.gear === 'GEAR_2_ACTIVE' ? 'healthy' : 'degraded';
            const healthClass = engine.health >= 40 ? 'healthy' :
                               engine.health >= 20 ? 'degraded' : 'critical';

            document.getElementById('engine-status').innerHTML = `
                Gear: <span class="status ${{gearClass}}">${{engine.gear || 'Unknown'}}</span>
                Health: <span class="status ${{healthClass}}">${{engine.health || 0}}/50</span>
                Cycles: ${{engine.cycles || 0}}
                ${{engine.in_grace ? '<span class="status degraded">GRACE</span>' : ''}}
            `;

            // Optimizer status
            const optClass = optimizer.mode === 'SURGE' ? 'critical' :
                            optimizer.mode === 'THROTTLE' ? 'degraded' : 'healthy';
            document.getElementById('optimizer-status').innerHTML = `
                8CV Mode: <span class="status ${{optClass}}">${{optimizer.mode || 'UNKNOWN'}}</span>
                Rate: ${{optimizer.token_rate || 0}} tok/s
                Conns: ${{optimizer.connections || 0}}
                Pressure: ${{optimizer.pressure || 0}}
            `;

            // Room grid
            const rooms = data.rooms || {{}};
            let roomsHtml = '';
            for (const [room_id, room] of Object.entries(rooms)) {{
                const statusClass = room.status === 'LOCKED' ? 'locked' :
                                   room.status === 'FAILED' ? 'failed' :
                                   room.status === 'DEGRADED' ? 'degraded' : 'healthy';
                roomsHtml += `
                    <div class="room-card">
                        <div class="room-name">${{room.label || room_id}}</div>
                        <div class="room-role">${{ROOM_ROLES[room_id] || ''}}</div>
                        <span class="status ${{statusClass}}">${{room.status || 'UNKNOWN'}}</span>
                    </div>
                `;
            }}
            document.getElementById('rooms-grid').innerHTML = roomsHtml;

            // Health chart
            const chart = data.chart || [];
            const chartEl = document.getElementById('health-chart');
            chartEl.innerHTML = '';
            if (chart.length > 0) {{
                const maxScore = Math.max(...chart.map(d => d.score), 50);
                chart.forEach((d, i) => {{
                    const bar = document.createElement('div');
                    bar.className = 'bar';
                    bar.style.left = (i * 6) + 'px';
                    bar.style.height = ((d.score / maxScore) * 180) + 'px';
                    bar.style.backgroundColor = d.score >= 40 ? '#0f0' : d.score >= 20 ? '#ff0' : '#f00';
                    bar.title = `Cycle ${{d.score}} — Top: ${{d.top}} Bottom: ${{d.bottom}}`;
                    chartEl.appendChild(bar);
                }});
            }}

            // Alerts
            const alerts = data.alerts || [];
            document.getElementById('alert-count').textContent = `(${{alerts.length}})`;
            const alertsEl = document.getElementById('alerts-content');
            alertsEl.innerHTML = '';
            alerts.forEach(alert => {{
                const line = document.createElement('div');
                line.innerHTML = `[${{alert.severity}}] ${{alert.event}}: ${{alert.detail}}`;
                line.style.color = alert.severity === 'CRITICAL' ? '#f00' :
                                   alert.severity === 'WARNING' ? '#ff0' : '#0f0';
                alertsEl.appendChild(line);
            }});
            alertsEl.scrollTop = alertsEl.scrollHeight;

            // AI feeds
            const feeds = data.feeds || {{}};
            let feedsHtml = '';
            for (const [ai, events] of Object.entries(feeds)) {{
                feedsHtml += `<h3>${{ai}}</h3><div class="log">`;
                events.forEach(event => {{
                    feedsHtml += `<div>[${{event.ts}}] ${{event.event}}</div>`;
                }});
                feedsHtml += `</div>`;
            }}
            document.getElementById('ai-feeds-content').innerHTML = feedsHtml;
        }}

        function sendCommand(command, params) {{
            fetch('/command', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{command, params}})
            }})
            .then(r => r.json())
            .then(data => {{
                if (data.ok) console.log('FC_FLOW command sent:', command);
                else console.error('Command failed:', data.error);
            }})
            .catch(err => console.error('Network error:', err));
        }}

        window.addEventListener('load', connectWebSocket);
    </script>
</body>
</html>"""


# ══════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════

def main():
    # Initialize FC_FLOW components
    token_feed = TokenFeed()
    commander = Commander(token_feed)
    engine = Figure8Engine(token_feed, commander)
    optimizer = ReactiveOptimizer(token_feed, engine)
    web_state = WebState(engine, commander, token_feed, optimizer)

    # Start 8CV engine
    engine.start()
    optimizer.start()

    # Start WebSocket server
    ws_server = WSServer(web_state, WEB_HOST, WS_PORT)
    ws_server.set_optimizer(optimizer)
    ws_server.start()

    # Start HTTP server
    MeshHTTPHandler.web_state = web_state
    MeshHTTPHandler.commander = commander
    MeshHTTPHandler.engine = engine
    MeshHTTPHandler.feed = token_feed

    http_server = HTTPServer((WEB_HOST, WEB_PORT), MeshHTTPHandler)

    print(f"⚡ FlowStation v{VERSION}")
    print("   FC_FLOW — Fuel Command Flow Line Own-Stack Withholding")
    print("   Sovereign Fuel Mesh | 8CV (8-Core-Velocity)")
    print("")
    print(f"   Web UI:    http://{WEB_HOST}:{WEB_PORT}")
    print(f"   WebSocket: ws://{WEB_HOST}:{WS_PORT}")
    print("")
    print("   Press Ctrl+C to initiate buzzkill shutdown")

    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        print("\n🔥 Buzzkill shutdown initiated...")
        engine.stop()
        optimizer.stop()
        ws_server._running = False
        print("   Sovereign Fuel Mesh offline. All keys burned.")


if __name__ == "__main__":
    main()