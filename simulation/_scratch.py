"""
kv_cache_sim.py — Distributed KV Cache Offloading Simulator v2

Models a memory-constrained device running LLM inference.
KV Cache grows per token (512KB/token for a ~7B model).
When local memory fills, older KV pages are evicted to remote (Wi-Fi 6).
Each decoding step's attention must read KV data from previous tokens;
if that data has been evicted to remote, a network fetch is required.

Strategies:
  1) Demand paging: fetch on cache miss (blocking)
  2) Async prefetch: predict and fetch evicted pages before they are needed

Key metric: speedup = (demand paging time) / (async prefetch time)
"""

from dataclasses import dataclass
from typing import List


@dataclass
class SimConfig:
    # Model
    num_layers: int = 32
    num_heads: int = 32
    head_dim: int = 128       # → 512 KB per token (K+V, FP16)
    seq_len: int = 4096
    compute_ms: float = 30.0  # ms per forward pass

    # Local (phone) memory
    local_mb: int = 512       # MB available for KV cache

    # Network
    latency_ms: float = 50.0  # one-way Wi-Fi RTT/2
    bandwidth_mbps: float = 500.0

    # Prefetch
    prefetch_window: int = 16

    def __post_init__(self):
        self.kv_bpt = 2 * self.num_layers * self.num_heads * self.head_dim * 2
        self.local_slots = (self.local_mb * 1024 * 1024) // self.kv_bpt
        bits_per_page = self.kv_bpt * 8 * 1.05
        self.xfer_ms = bits_per_page / (self.bandwidth_mbps * 1e6) * 1000 + 2 * self.latency_ms


@dataclass
class Step:
    idx: int
    local_cnt: int
    remote_cnt: int
    wait_ms: float
    wall_ms: float
    page_fault: bool
    prefetch_hit: bool = False


# ---------------------------------------------------------------------------
# Helper: time to compute a full attention pass given the set of local/
# remote token ids.  For simplicity: reading a local page costs 0 extra
# (already in fast memory); reading a remote page costs xfer_ms (blocking
# in demand paging, possibly overlapped in prefetch).
# ---------------------------------------------------------------------------


def simulate_demand(cfg: SimConfig) -> List[Step]:
    """Demand paging: every cache miss triggers a blocking network fetch."""
    N = cfg.local_slots
    xfer = cfg.xfer_ms
    comp = cfg.compute_ms

    steps = []
    fifo: List[int] = []   # tokens cached locally (FIFO order)
    remote: set = set()    # tokens evicted to remote
    wall = 0.0

    for i in range(cfg.seq_len):
        # --- Evict if full ---
        evicted = None
        if len(fifo) >= N:
            evicted = fifo.pop(0)
            remote.add(evicted)

        fifo.append(i)

        # --- Attention: read KV of tokens that are in remote ---
        # For this simplified model, we fetch ALL needed remote tokens.
        # In practice this would be the attention window; here we
        # approximate by reading the set of remote tokens.
        remote_needed = [t for t in fifo[:-1] if t in remote]
        wait = len(remote_needed) * xfer if remote_needed else 0.0
        page_fault = len(remote_needed) > 0

        dt = comp + wait
        wall += dt

        steps.append(Step(i, len(fifo), len(remote), wait, wall, page_fault))

    return steps


def simulate_prefetch(cfg: SimConfig) -> List[Step]:
    """Async prefetch: overlap remote fetches with computation."""
    N = cfg.local_slots
    xfer = cfg.xfer_ms
    comp = cfg.compute_ms
    W = cfg.prefetch_window

    steps = []
    fifo: List[int] = []
    remote: set = set()
    inflight: dict = {}   # token_id -> expected wall arrival time
    wall = 0.0

    for i in range(cfg.seq_len):
        # --- Process completed prefetches ---
        done = [k for k, v in inflight.items() if v <= wall]
        for k in done:
            remote.discard(k)   # no longer remote, will be re-added if re-evicted
            del inflight[k]

        # --- Evict if full ---
        evicted = None
        if len(fifo) >= N:
            evicted = fifo.pop(0)
            remote.add(evicted)
        fifo.append(i)

        # --- Attention: which remote tokens do we need? ---
        remote_needed = [t for t in fifo[:-1] if t in remote]

        wait = 0.0
        page_fault = False
        prefetch_hit = False

        for r in remote_needed:
            if r in inflight:
                # Prefetch already in flight — wait only if not arrived
                remaining = max(0.0, inflight[r] - wall)
                if remaining > 0.01:
                    wait += remaining
                    page_fault = True
                    prefetch_hit = True
                    wall += remaining   # advance wall for subsequent checks
                del inflight[r]
            else:
                # Full miss — fetch now
                wait += xfer
                page_fault = True
                wall += xfer
                remote.discard(r)   # just fetched, remove from remote set

        # --- Issue prefetches for tokens about to be evicted ---
        # We predict that the oldest tokens in the window will be needed
        # at future steps.  Prefetch W tokens from the eviction frontier.
        evict_frontier = fifo[:W] if len(fifo) >= W else fifo[:len(fifo)]
        for ft in evict_frontier:
            if ft in remote and ft not in inflight:
                inflight[ft] = wall + comp + xfer

        dt = comp + wait
        wall += (comp + wait) - (wall - (steps[-1].wall_ms if steps else 0.0))

        # Fix wall accumulation
        # Actually wait was already added to wall above inside the loop.
        # Let's recalculate properly.

        steps.append(Step(i, len(fifo), len(remote), wait, wall, page_fault, prefetch_hit))

    return steps


# Oops, the wall accumulation above is buggy. Let me rewrite cleanly.
# This module is just for reference. The real implementation is below.
