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
from pipeline_executor import PipelineExecutor

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
            seed = hashlib.sha256(entropy + state + threat.to_bytes(4, "big")).digest()
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






class VaultManager:
    """
    Nested vault — integrates with 8CV topology.
    Stores tokens, AI notes, and fuel reserves.
    """
    def __init__(self):
        self.vault_root = VAULT_DIR
        self.token_recycler = TokenRecycler(self)
        self.ai_notes = AINoteStore(self)
        self.fuel_reserves = FuelReserveStore(self)
        self._ensure_structure()
    
    def _ensure_structure(self):
        """Build vault directory tree."""
        os.makedirs(f"{self.vault_root}/tokens", exist_ok=True)
        os.makedirs(f"{self.vault_root}/ai_notes", exist_ok=True)
        os.makedirs(f"{self.vault_root}/fuel_reserves", exist_ok=True)


class TokenRecycler:
    """
    Gemini token recycling — 50%+ cost savings.
    Stores tokens with metadata, rotates through WARM/COLD tiers.
    """
    def __init__(self, vault):
        self.vault = vault
        self.pool_path = f"{vault.vault_root}/tokens/gemini_pool.json"
        self.metadata_path = f"{vault.vault_root}/tokens/token_metadata.json"
        self._pool = []
        self._metadata = {}
        self._load()
    
    def _load(self):
        """Load existing token pool from disk."""
        if os.path.exists(self.pool_path):
            with open(self.pool_path, 'r') as f:
                self._pool = json.load(f)
        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, 'r') as f:
                self._metadata = json.load(f)
    
    def _save(self):
        """Persist token pool to disk."""
        with open(self.pool_path, 'w') as f:
            json.dump(self._pool, f, indent=2)
        with open(self.metadata_path, 'w') as f:
            json.dump(self._metadata, f, indent=2)
    
    def deposit(self, tokens: list, source: str = "gemini_api"):
        """Deposit tokens into the pool."""
        timestamp = time.time()
        for token in tokens:
            token_id = hashlib.sha256(token.encode()).hexdigest()[:16]
            self._pool.append({
                "token": token,
                "token_id": token_id,
                "deposited": timestamp,
                "source": source,
                "tier": "WARM",
                "use_count": 0,
            })
        self._save()
        write_audit("TOKEN_DEPOSIT", f"Deposited {len(tokens)} tokens from {source}")
    
    def withdraw(self, count: int = 1) -> list:
        """Withdraw tokens from pool for reuse."""
        if len(self._pool) < count:
            return []
        
        warm = [t for t in self._pool if t["tier"] == "WARM"]
        cold = [t for t in self._pool if t["tier"] == "COLD"]
        
        withdrawn = []
        for token_entry in (warm + cold)[:count]:
            withdrawn.append(token_entry["token"])
            token_entry["use_count"] += 1
            token_entry["last_used"] = time.time()
            
            if token_entry["use_count"] >= 3:
                token_entry["tier"] = "COLD"
        
        self._save()
        write_audit("TOKEN_WITHDRAW", f"Withdrew {len(withdrawn)} tokens")
        return withdrawn
    
    def rotate_tiers(self):
        """8CV-aware tier rotation."""
        now = time.time()
        rotated = 0
        for token_entry in self._pool:
            age = now - token_entry.get("deposited", now)
            
            if token_entry["tier"] == "COLD" and age > 600:
                token_entry["tier"] = "WARM"
                rotated += 1
            
            elif token_entry["tier"] == "WARM" and age > 1800:
                token_entry["tier"] = "COLD"
                rotated += 1
        
        if rotated > 0:
            self._save()
    
    def get_stats(self) -> dict:
        """Return pool statistics for monitoring."""
        warm = len([t for t in self._pool if t["tier"] == "WARM"])
        cold = len([t for t in self._pool if t["tier"] == "COLD"])
        total_uses = sum(t.get("use_count", 0) for t in self._pool)
        
        return {
            "total_tokens": len(self._pool),
            "warm_tokens": warm,
            "cold_tokens": cold,
            "total_reuses": total_uses,
            "savings_estimate": f"{(total_uses / max(len(self._pool), 1)) * 50:.1f}%"
        }


class AINoteStore:
    """
    Persistent AI memory — survives session wipes.
    """
    def __init__(self, vault):
        self.vault = vault
        self.notes_dir = f"{vault.vault_root}/ai_notes"
    
    def _note_path(self, ai_name: str) -> str:
        return f"{self.notes_dir}/{ai_name}_notes.json"
    
    def read_notes(self, ai_name: str) -> dict:
        """AI clocks in — load persistent notes."""
        path = self._note_path(ai_name)
        if not os.path.exists(path):
            return {
                "agent": ai_name,
                "notes": [],
                "last_session": None,
                "total_sessions": 0
            }
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        write_audit("AI_CLOCK_IN", f"{ai_name} loaded {len(data.get('notes', []))} notes")
        return data
    
    def write_note(self, ai_name: str, note: str, tag: str = "general"):
        """AI writes a note during session."""
        path = self._note_path(ai_name)
        data = self.read_notes(ai_name)
        
        data["notes"].append({
            "timestamp": datetime.now().isoformat(),
            "note": note,
            "tag": tag
        })
        
        if len(data["notes"]) > 100:
            data["notes"] = data["notes"][-100:]
        
        data["last_session"] = datetime.now().isoformat()
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        
        write_audit("AI_NOTE_WRITE", f"{ai_name}: {tag}")
    
    def clock_out(self, ai_name: str):
        """AI clocks out — increment session count."""
        path = self._note_path(ai_name)
        data = self.read_notes(ai_name)
        data["total_sessions"] = data.get("total_sessions", 0) + 1
        data["last_session"] = datetime.now().isoformat()
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        
        write_audit("AI_CLOCK_OUT", f"{ai_name} session #{data['total_sessions']}")


class FuelReserveStore:
    """Tracks fuel consumption per room in 8CV topology."""
    def __init__(self, vault):
        self.vault = vault
        self.reserves_dir = f"{vault.vault_root}/fuel_reserves"
    
    def _reserve_path(self, room_id: str) -> str:
        return f"{self.reserves_dir}/{room_id}_reserve.json"
    
    def get_reserve(self, room_id: str) -> dict:
        path = self._reserve_path(room_id)
        if not os.path.exists(path):
            return {
                "room_id": room_id,
                "room_name": ROOMS.get(room_id, "Unknown"),
                "fuel_level": 1000,
                "tier": "WARM",
                "last_refill": time.time()
            }
        
        with open(path, 'r') as f:
            return json.load(f)
    
    def consume_fuel(self, room_id: str, amount: int):
        """Consume fuel when AI makes API call."""
        reserve = self.get_reserve(room_id)
        reserve["fuel_level"] -= amount
        
        if reserve["fuel_level"] < 100:
            reserve["tier"] = "CRITICAL"
            write_audit("FUEL_CRITICAL", f"{room_id} fuel at {reserve['fuel_level']}")
        
        with open(self._reserve_path(room_id), 'w') as f:
            json.dump(reserve, f, indent=2)
    
    def refill(self, room_id: str, amount: int):
        """Refill room fuel."""
        reserve = self.get_reserve(room_id)
        reserve["fuel_level"] += amount
        reserve["last_refill"] = time.time()
        reserve["tier"] = "WARM"
        
        with open(self._reserve_path(room_id), 'w') as f:
            json.dump(reserve, f, indent=2)




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
        self._vault = VaultManager()
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
                import traceback; self._log.error(f"8CV cycle error: {e}"); traceback.print_exc()
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
        self._vault.token_recycler.rotate_tiers()

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
            int(self._gear.value).to_bytes(1, "big") +
            str(time.monotonic()).encode() +
            b"".join(str(self._keys.get(r).split).encode() for r in sorted(self._keys.all_splits()))
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
                    try:
                        with open(path, 'r') as f:
                            data = json.load(f)
                    except (json.JSONDecodeError, FileNotFoundError):
                        data = {"agent": ai, "events": []}
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
            print(f'✅ WebSocket bound to {self._host}:{self._port}')
            srv.listen(MAX_WS_CLIENTS)
            srv.settimeout(1.0)
            self._log.info(f"WebSocket listening on {self._host}:{self._port}")
            print(f'🔍 WebSocket loop starting, _running={self._running}')
            while self._running:
                try:
                    conn, addr = srv.accept()
                    threading.Thread(target=self._handshake, args=(conn, addr), daemon=True).start()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self._running:
                        print(f'❌ WebSocket accept loop crashed: {e}')
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


    def broadcast(self, room: str, message: str):
        """Send a message to a specific room feed"""
        try:
            # Update the room's feed in web_state
            if hasattr(self._web_state, 'rooms') and room in self._web_state.rooms:
                self._web_state.rooms[room].add_message(message)
            # Immediate push to connected clients
            with self._lock:
                clients = list(self._clients)
            for client in clients:
                if client.alive:
                    try:
                        # Send just the room update
                        update = json.dumps({"room": room, "message": message})
                        client.send_text(update)
                    except Exception:
                        client.alive = False
        except Exception as e:
            self._log.warning(f"Broadcast to {room} failed: {e}")


# ── HTTP SERVER ──





class MeshHTTPHandler(BaseHTTPRequestHandler):
    """Serves Web Command Center + handles API commands."""

    web_state = None
    commander = None
    engine = None
    feed = None

    def log_message(self, fmt, *args):
        pass


    def _handle_ai_notes(self):
        import json
        try:
            notes = {"notes": [], "status": "ok"}
            body = json.dumps(notes).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            self.send_response(500)
            self.end_headers()


    def _handle_ai_notes(self):
        """Read AI notes — called when AI clocks in."""
        ai_name = self.path.split('/')[-1]
        notes = self.engine._vault.ai_notes.read_notes(ai_name)
        self._json_response(notes)

    def _handle_ai_notes_write(self):
        """Write AI note — called during session."""
        ai_name = self.path.split('/')[-1]
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length).decode())
        
        note = body.get('note', '')
        tag = body.get('tag', 'general')
        
        self.engine._vault.ai_notes.write_note(ai_name, note, tag)
        self._json_response({"status": "saved"})

    def _handle_ai_clock_out(self):
        """AI clocks out — persist session count."""
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length).decode())
        ai_name = body.get('ai_name', '')
        
        self.engine._vault.ai_notes.clock_out(ai_name)
        self._json_response({"status": "clocked_out"})
    def do_GET(self):
        if self.path.startswith("/api/fuel-reserve/"):
            self._handle_fuel_reserve()
            return
        if self.path.startswith("/api/8cv-status"):
            self._handle_8cv_status()
            return
        if self.path.startswith("/api/8cv-history"):
            self._handle_8cv_history()
            return
        if self.path.startswith("/api/ai-notes"):
            self._handle_ai_notes()
            return
        if self.path.startswith("/api/ai-locks"):
            self._handle_ai_locks()
            return
        if self.path.startswith("/api/load-from-room"):
            self._handle_load_from_room()
            return
        if self.path.startswith("/api/load-from-room"):
            self._handle_load_from_room()
            return
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
        if self.path == "/api/token-deposit":
            self._handle_token_deposit()
            return
        if self.path == "/api/token-withdraw":
            self._handle_token_withdraw()
            return
        if self.path.startswith("/api/ai-notes-write/"):
            self._handle_ai_notes_write()
            return
        if self.path == "/api/ai-clock-out":
            self._handle_ai_clock_out()
            return
        if self.path == "/api/ai-observe":
            self._handle_ai_observe()
            return
        if self.path == "/api/commander-override":
            self._handle_commander_override()
            return
        if self.path == "/api/ai-chat":
            self._handle_ai_chat()
            return
        if self.path == "/api/ai-chat-gemini":
            self._handle_ai_chat_gemini()
            return
        if self.path == "/api/ai-wipe-memory":
            self._handle_ai_wipe_memory()
            return
        if self.path == "/api/ai-logout":
            self._handle_ai_logout()
            return
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
        with open('/root/Sovereign_FC_FLOWStation/rooms/compiled.html') as f:
            html = f.read()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(html.encode())))
        self._cors_headers()
        self.end_headers()
        try:
            self.wfile.write(html.encode())
        except BrokenPipeError:
            pass  # Client disconnected

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
                'FORGE', 'SPLIT', 'SORT', 'INTEGRATE', 'BUILD',
            }
            if cmd not in valid:
                self._json_response({"ok": False, "error": f"Unknown command: {cmd}"}, 400)
                return
            
            # Route pipeline commands to executor
            pipeline_cmds = {'FORGE', 'SPLIT', 'SORT', 'INTEGRATE', 'BUILD'}
            if cmd in pipeline_cmds:
                if hasattr(self.__class__, 'pipeline_executor'):
                    self.__class__.pipeline_executor.execute(cmd, params)
                else:
                    self._json_response({"ok": False, "error": "Pipeline executor not available"}, 500)
                    return
            else:
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


    def _handle_token_stats(self):
        """Return token recycling statistics."""
        stats = self.engine._vault.token_recycler.get_stats()
        self._json_response(stats)


    def _handle_token_deposit(self):
        """Deposit tokens into recycling pool."""
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length).decode())
        
        tokens = body.get('tokens', [])
        source = body.get('source', 'api')
        
        self.engine._vault.token_recycler.deposit(tokens, source)
        self._json_response({"status": "deposited", "count": len(tokens)})
    
    def _handle_token_withdraw(self):
        """Withdraw tokens from recycling pool."""
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length).decode())
        
        count = body.get('count', 1)
        tokens = self.engine._vault.token_recycler.withdraw(count)
        
        self._json_response({"tokens": tokens, "count": len(tokens)})
    
    def _handle_fuel_reserve(self):
        """Get fuel reserve for a room."""
        room_id = self.path.split('/')[-1]
        reserve = self.engine._vault.fuel_reserves.get_reserve(room_id)
        self._json_response(reserve)


    def _call_gemini_api(self, prompt: str) -> dict:
        """Call Gemini REST API (2026 v1beta format)."""
        api_key = self._load_gemini_key()
        if not api_key:
            return {"error": "API key not configured"}
        
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }
        
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key
        }
        
        try:
            import requests
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if "candidates" in data and len(data["candidates"]) > 0:
                    content = data["candidates"][0]["content"]
                    if "parts" in content and len(content["parts"]) > 0:
                        return {"response": content["parts"][0]["text"]}
                return {"error": "No response from Gemini"}
            else:
                return {"error": f"API error {response.status_code}: {response.text}"}
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}

    # Gemini 3-Tier Model Matrix
    GEMINI_MODELS = {
        "tier1_heavy": "gemini-3.1-pro-preview",      # Heavy reasoning
        "tier2_workhorse": "gemini-3.5-flash",        # Main operational
        "tier3_lite": "gemini-3.1-flash-lite"         # Ultra-low cost
    }

    def _call_gemini_api(self, prompt: str, tier: str = "tier3_lite") -> dict:
        """Call Gemini REST API with 3-tier routing (2026 AQ. key format)."""
        api_key = self._load_gemini_key()
        if not api_key:
            return {"error": "API key not configured"}
        
        model = self.GEMINI_MODELS.get(tier, self.GEMINI_MODELS["tier3_lite"])
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }
        
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key
        }
        
        try:
            import requests
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if "candidates" in data and len(data["candidates"]) > 0:
                    content = data["candidates"][0]["content"]
                    if "parts" in content and len(content["parts"]) > 0:
                        return {"response": content["parts"][0]["text"], "model": model}
                return {"error": "No response from Gemini"}
            else:
                return {"error": f"API error {response.status_code}: {response.text}"}
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}

    def _handle_ai_chat(self):
        """Handle AI chat requests (OpenAI-compatible endpoint)."""
        try:
            length = int(self.headers.get('Content-Length', 0))
            if length == 0:
                self._json_response({"error": "No request body"}, 400)
                return
            
            body = json.loads(self.rfile.read(length).decode())
            messages = body.get('messages', [])
            
            if not messages:
                self._json_response({"error": "No messages provided"}, 400)
                return
            
            # Extract last user message
            user_message = messages[-1].get('content', '')
            
            # TODO: Integrate with actual LLM API (OpenAI, Anthropic, etc.)
            # For now, return a placeholder response
            response_text = f"[AI Response Placeholder] Received: {user_message[:50]}..."
            
            self._json_response({
                "id": f"chat-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": body.get('model', 'gpt-4'),
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": len(user_message) // 4,
                    "completion_tokens": len(response_text) // 4,
                    "total_tokens": (len(user_message) + len(response_text)) // 4
                }
            })
        except Exception as e:
            self._json_response({"error": str(e)}, 500)
    
    def _handle_ai_chat_gemini(self):
        """Handle Gemini-specific chat requests."""
        try:
            length = int(self.headers.get('Content-Length', 0))
            if length == 0:
                self._json_response({"error": "No request body"}, 400)
                return
            
            body = json.loads(self.rfile.read(length).decode())
            prompt = body.get('prompt', '')
            
            if not prompt:
                self._json_response({"error": "No prompt provided"}, 400)
                return
            
            # TODO: Integrate with actual Gemini API
            response_text = f"[Gemini Placeholder] Received: {prompt[:50]}..."
            
            self._json_response({
                "response": response_text,
                "model": "gemini-pro",
                "timestamp": time.time()
            })
        except Exception as e:
            self._json_response({"error": str(e)}, 500)


    def _load_gemini_key(self):
        """Load Gemini API key from vault."""
        key_file = os.path.join(os.path.dirname(__file__), "vault/gemini_key.txt")
        if os.path.exists(key_file):
            with open(key_file, 'r') as f:
                return f.read().strip()
        return None
    
    
    def _handle_ai_chat(self):
        """Handle AI chat with Gemini REST API."""
        try:
            length = int(self.headers.get('Content-Length', 0))
            if length == 0:
                self._json_response({"error": "No request body"}, 400)
                return
            
            body = json.loads(self.rfile.read(length).decode())
            messages = body.get('messages', [])
            
            if not messages:
                self._json_response({"error": "No messages provided"}, 400)
                return
            
            # Build conversation text from messages
            conversation = "\n".join([
                f"{msg['role']}: {msg['content']}" 
                for msg in messages
            ])
            
            # Call Gemini
            result = self._call_gemini_api(conversation)
            
            if "error" in result:
                self._json_response({"error": result["error"]}, 500)
                return
            
            response_text = result["response"]
            
            # Return OpenAI-compatible format
            self._json_response({
                "id": f"chat-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "gemini-pro",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": len(conversation) // 4,
                    "completion_tokens": len(response_text) // 4,
                    "total_tokens": (len(conversation) + len(response_text)) // 4
                }
            })
            
        except Exception as e:
            self._json_response({"error": f"Handler error: {str(e)}"}, 500)
    
    def _handle_ai_chat_gemini(self):
        """Handle direct Gemini chat (simplified endpoint)."""
        try:
            length = int(self.headers.get('Content-Length', 0))
            if length == 0:
                self._json_response({"error": "No request body"}, 400)
                return
            
            body = json.loads(self.rfile.read(length).decode())
            prompt = body.get('prompt', '')
            
            if not prompt:
                self._json_response({"error": "No prompt provided"}, 400)
                return
            
            # Call Gemini
            result = self._call_gemini_api(prompt)
            
            if "error" in result:
                self._json_response({"error": result["error"]}, 500)
                return
            
            self._json_response({
                "response": result["response"],
                "model": "gemini-pro",
                "timestamp": time.time()
            })
            
        except Exception as e:
            self._json_response({"error": f"Handler error: {str(e)}"}, 500)

# ── HTML BUILDER ──





    def _handle_ai_notes(self):
        """AI notes — sovereign session memory bank."""
        import json
        import os

        ai_name = self.path.split("/")[-1] if "/" in self.path else "unknown"
        notes_path = os.path.join("ai_feeds", f"{ai_name}_notes.json")

        try:
            if os.path.exists(notes_path):
                with open(notes_path, "r") as f:
                    notes = json.load(f)
            else:
                notes = {
                    "agent":    ai_name,
                    "entries":  [],
                    "last_seen": None
                }

            body = json.dumps(notes).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        except Exception as e:
            self.send_response(500)
            self.end_headers()

    def _handle_ai_notes_write(self):
        """AI writes a note to its memory bank."""
        import json
        import os
        from datetime import datetime

        ai_name = self.path.split("/")[-1] if "/" in self.path else "unknown"
        notes_path = os.path.join("ai_feeds", f"{ai_name}_notes.json")

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            new_entry = json.loads(body)

            if os.path.exists(notes_path):
                with open(notes_path, "r") as f:
                    notes = json.load(f)
            else:
                notes = {"agent": ai_name, "entries": [], "last_seen": None}

            notes["entries"].append({
                "ts":    datetime.now().isoformat(),
                "note":  new_entry.get("note", ""),
                "tag":   new_entry.get("tag", "general")
            })
            notes["last_seen"] = datetime.now().isoformat()

            # Keep last 100 notes — old ones drop off
            if len(notes["entries"]) > 100:
                notes["entries"] = notes["entries"][-100:]

            with open(notes_path, "w") as f:
                json.dump(notes, f, indent=2)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"saved"}')

        except Exception as e:
            self.send_response(500)
            self.end_headers()

def build_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>THE 4-ROOM COMMAND CENTER</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0a0e27;
            color: #00ff00;
            font-family: 'Courier New', monospace;
            overflow: hidden;
            height: 100vh;
        }
        .header {
            text-align: center;
            padding: 20px;
            background: linear-gradient(90deg, #0a0e27, #1a1e47, #0a0e27);
            border-bottom: 2px solid #00ff00;
        }
        .header h1 {
            color: #00ffff;
            font-size: 24px;
            letter-spacing: 4px;
        }
        .header .subtitle {
            color: #888;
            font-size: 12px;
            font-style: italic;
        }
        .header .status {
            position: absolute;
            top: 20px;
            right: 20px;
            color: #ff00ff;
            font-size: 14px;
        }
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: 1fr 1fr;
            height: calc(100vh - 120px);
            gap: 2px;
            padding: 2px;
        }
        .room {
            border: 2px solid;
            padding: 10px;
            overflow-y: auto;
            position: relative;
        }
        .room-header {
            font-weight: bold;
            font-size: 16px;
            margin-bottom: 10px;
            padding: 5px;
            border-bottom: 1px solid;
        }
        .room-content {
            font-size: 13px;
            line-height: 1.6;
        }
        #room1 { border-color: #00ffff; background: rgba(0, 255, 255, 0.05); }
        #room1 .room-header { color: #00ffff; border-color: #00ffff; }
        
        #room2 { border-color: #00ff00; background: rgba(0, 255, 0, 0.05); }
        #room2 .room-header { color: #00ff00; border-color: #00ff00; }
        
        #room3 { border-color: #ffaa00; background: rgba(255, 170, 0, 0.05); }
        #room3 .room-header { color: #ffaa00; border-color: #ffaa00; }
        
        #room4 { border-color: #ff00ff; background: rgba(255, 0, 255, 0.05); }
        #room4 .room-header { color: #ff00ff; border-color: #ff00ff; }
        
        .cmd-line { margin: 5px 0; }
        .cmd-line::before { content: "→ "; color: #666; }
        
        .terminal-input {
            background: rgba(0,0,0,0.5);
            border: 1px solid #ffaa00;
            color: #00ff00;
            font-family: 'Courier New', monospace;
            padding: 8px;
            width: 100%;
            margin-top: 10px;
        }
        .terminal-output {
            background: rgba(0,0,0,0.3);
            padding: 10px;
            margin: 5px 0;
            border-left: 3px solid #ffaa00;
            color: #aaa;
        }
        .ai-msg {
            background: rgba(255,0,255,0.1);
            border-left: 3px solid #ff00ff;
            padding: 8px;
            margin: 5px 0;
            color: #ff00ff;
        }
        .footer {
            display: flex;
            justify-content: space-around;
            padding: 10px;
            background: #0a0e27;
            border-top: 2px solid #00ff00;
        }
        .footer button {
            background: transparent;
            border: 2px solid #00ff00;
            color: #00ff00;
            padding: 8px 20px;
            font-family: 'Courier New', monospace;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
        }
        .footer button:hover {
            background: #00ff00;
            color: #0a0e27;
        }
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #0a0e27; }
        ::-webkit-scrollbar-thumb { background: #00ff00; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="status">● LIVE</div>
        <h1>THE 4-ROOM COMMAND CENTER</h1>
        <div class="subtitle">Bad MF Box architecture — applied to sovereign development</div>
    </div>

    <div class="grid">
        <!-- Room 1: Command Post -->
        <div class="room" id="room1">
            <div class="room-header">[ 1 ] COMMAND POST</div>
            <div class="room-content">
                <div class="cmd-line">Pipeline control</div>
                <div class="cmd-line">Room management</div>
                <div class="cmd-line">Engine status</div>
                <div class="cmd-line">Lock / Unlock</div>
                <div style="margin-top: 20px; color: #00ffff;">
                    <strong>8CV Status:</strong><br>
                    Gear: <span id="gear">GEAR_2_ACTIVE</span><br>
                    Health: <span id="health">50/50</span><br>
                    Cycles: <span id="cycles">0</span>
                </div>
            </div>
        </div>

        <!-- Room 2: File Status -->
        <div class="room" id="room2">
            <div class="room-header">[ 2 ] FILE STATUS</div>
            <div class="room-content">
                <div class="cmd-line">Current file</div>
                <div class="cmd-line">Last edits</div>
                <div class="cmd-line">Lock status</div>
                <div class="cmd-line">Diff view</div>
                <div id="file-status" style="margin-top: 20px; color: #00ff00;">
                    <strong>Room States:</strong><br>
                    <div id="room-list"></div>
                </div>
            </div>
        </div>

        <!-- Room 4: AI Chat -->
        <div class="room" id="room4">
            <div class="room-header">[ 4 ] AI CHAT</div>
            <div class="room-content">
                <div class="cmd-line">AI sees your work</div>
                <div class="cmd-line">Edits with you</div>
                <div class="cmd-line">Live suggestions</div>
                <div class="cmd-line">Sovereign access</div>
                <div id="ai-feed" style="margin-top: 10px;"></div>
            </div>
        </div>

        <!-- Room 3: Terminal -->
        <div class="room" id="room3">
            <div class="room-header">[ 3 ] TERMINAL</div>
            <div class="room-content">
                <div class="cmd-line">Live execution</div>
                <div class="cmd-line">Input → tools</div>
                <div class="cmd-line">File system</div>
                <div class="cmd-line">Build output</div>
                <div id="terminal-output"></div>
                <input type="text" class="terminal-input" id="terminal-input" placeholder="$ enter command...">
            </div>
        </div>
    </div>

    <div class="footer">
        <button onclick="sendCommand('FORGE')">FORGE</button>
        <button onclick="sendCommand('SPLIT')">SPLIT</button>
        <button onclick="sendCommand('SORT')">SORT</button>
        <button onclick="sendCommand('INTEGRATE')">INTEGRATE</button>
        <button onclick="sendCommand('BUILD')">BUILD</button>
    </div>

    <script>
        let ws;
        let wsReconnectTimer;

        function connectWebSocket() {
            ws = new WebSocket('ws://localhost:8081');
            
            ws.onopen = () => {
                console.log('WebSocket connected');
                document.querySelector('.status').textContent = '● LIVE';
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    handleWebSocketMessage(data);
                } catch (e) {
                    console.error('Parse error:', e);
                }
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

            ws.onclose = () => {
                document.querySelector('.status').textContent = '● RECONNECTING';
                wsReconnectTimer = setTimeout(connectWebSocket, 2000);
            };
        }

        function handleWebSocketMessage(data) {
            if (data.event === 'CYCLE') {
                document.getElementById('gear').textContent = data.payload.gear;
                document.getElementById('health').textContent = `${data.payload.health}/50`;
                document.getElementById('cycles').textContent = data.payload.cycle;
            } else if (data.event === 'ROOM_UPDATE') {
                updateRoomList(data.payload);
            } else if (data.event === 'AI_MESSAGE') {
                addAIMessage(data.payload);
            } else if (data.event === 'TERMINAL_OUTPUT') {
                addTerminalOutput(data.payload);
            }
        }

        function updateRoomList(rooms) {
            const roomList = document.getElementById('room-list');
            roomList.innerHTML = '';
            for (const [name, status] of Object.entries(rooms)) {
                const color = status === 'HEALTHY' ? '#00ff00' : '#ff0000';
                roomList.innerHTML += `<div style="color: ${color};">${name}: ${status}</div>`;
            }
        }

        function addAIMessage(msg) {
            const feed = document.getElementById('ai-feed');
            const div = document.createElement('div');
            div.className = 'ai-msg';
            div.textContent = msg;
            feed.appendChild(div);
            feed.scrollTop = feed.scrollHeight;
        }

        function addTerminalOutput(output) {
            const terminal = document.getElementById('terminal-output');
            const div = document.createElement('div');
            div.className = 'terminal-output';
            div.textContent = output;
            terminal.appendChild(div);
            terminal.scrollTop = terminal.scrollHeight;
        }

        function sendCommand(cmd) {
            fetch('/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: cmd, params: {} })
            }).then(r => r.json()).then(data => {
                addTerminalOutput(`> ${cmd}: ${JSON.stringify(data)}`);
            });
        }

        document.getElementById('terminal-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const cmd = e.target.value;
                addTerminalOutput(`$ ${cmd}`);
                // Send to backend
                e.target.value = '';
            }
        });

        connectWebSocket();

        // Fetch initial state
        fetch('/state').then(r => r.json()).then(data => {
            if (data.turf && data.turf.rooms) {
                updateRoomList(data.turf.rooms);
            }
        });
    </script>
</body>
</html>
"""

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
    print(f'   WebSocket thread started')

    # Initialize pipeline executor
    pipeline_executor = PipelineExecutor(ws_server)

    # Start HTTP server
    MeshHTTPHandler.web_state = web_state
    MeshHTTPHandler.commander = commander
    MeshHTTPHandler.engine = engine
    MeshHTTPHandler.feed = token_feed
    MeshHTTPHandler.ws_server = ws_server
    MeshHTTPHandler.pipeline_executor = pipeline_executor

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

    def _handle_token_stats(self):
        """Return token recycling statistics."""
        stats = self.engine._vault.token_recycler.get_stats()
        self._json_response(stats)
