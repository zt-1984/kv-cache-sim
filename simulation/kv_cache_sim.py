"""
kv_cache_sim.py - Distributed KV Cache Offloading Simulator

MODEL
=====
LLM autoregressive decoding with KV cache offloading.

Each token produces 512 KB of KV data (7B model, FP16).
Local memory holds N tokens.  When full, old tokens are evicted to
remote (PC over Wi-Fi 6).  Eviction is a write to remote storage.

The eviction pipeline:
  Each eviction takes xfer_ms to complete (serialize + transmit + ack).
  With demand paging: eviction is SYNCHRONOUS — the step waits.
  With async prefetch: evictions are pipelined.  While computing step
    i, we are also evicting data from step i-K (where K is pipeline
    depth).  With enough pipeline depth (K >= xfer_ms / comp_ms + 1),
    evictions are fully hidden.

Speedup: speedup = (S*comp + N*xfer) / max(S*comp, N*xfer/depth)
  where S = seq_len, N = num evictions, depth = pipeline capacity
  In the ideal case (depth >= xfer/comp): full overlap, speedup ≈ 3.7x
"""

from dataclasses import dataclass
from typing import List


@dataclass
class SimConfig:
    num_layers: int = 32
    num_heads: int = 32
    head_dim: int = 128
    seq_len: int = 4096
    compute_ms: float = 30.0
    local_memory: int = 512 * 1024 * 1024
    latency_ms: float = 50.0
    bandwidth_mbps: float = 500.0
    prefetch_window: int = 16      # pipeline depth (inflight evictions)

    kv_bpt: int = 0
    local_slots: int = 0
    xfer_ms: float = 0.0

    def __post_init__(self):
        self.kv_bpt = 2 * self.num_layers * self.num_heads * self.head_dim * 2
        self.local_slots = self.local_memory // self.kv_bpt
        bits = self.kv_bpt * 8 * 1.05
        self.xfer_ms = bits / (self.bandwidth_mbps * 1e6) * 1000 + 2 * self.latency_ms


@dataclass
class StepRec:
    idx: int
    local_cnt: int
    evictions_done: int
    wait_ms: float
    wall_ms: float
    stall_type: str   # "compute", "eviction", "both"


# ===================================================================
# Demand paging — synchronous eviction
# ===================================================================

def simulate_demand(cfg: SimConfig) -> List[StepRec]:
    N, comp, xfer = cfg.local_slots, cfg.compute_ms, cfg.xfer_ms
    fifo: List[int] = []
    wall = 0.0
    steps = []
    evictions = 0

    for i in range(cfg.seq_len):
        wait = 0.0
        if len(fifo) >= N:
            fifo.pop(0)
            wait = xfer
            evictions += 1
        fifo.append(i)

        stall = comp + wait
        wall += stall
        steps.append(StepRec(i, len(fifo), evictions, wait, wall,
                             "eviction" if wait > 0 else "compute"))

    return steps


# ===================================================================
# Async prefetch — pipelined eviction
# ===================================================================

def simulate_prefetch(cfg: SimConfig) -> List[StepRec]:
    """
    Eviction pipeline with capacity W (= prefetch_window).
    At any time, up to W evictions can be in-flight.
    The link has throughput 1/xfer_ms evictions per ms.
    A new eviction can start if fewer than W are in-flight.

    Step i scheduling:
      1. Submit eviction for oldest token (if fifo full).
         If pipeline is full (W inflight), wait for one to complete.
      2. Compute (comp ms).  During compute, evictions make progress.
      3. Record wall time.
    """
    N, comp, xfer = cfg.local_slots, cfg.compute_ms, cfg.xfer_ms
    W = cfg.prefetch_window

    fifo: List[int] = []
    wall = 0.0
    steps = []
    evictions = 0

    # Pipeline: eviction completions tracked as future wall times
    # Completion[k] = wall time when eviction k will finish
    completions: List[float] = []

    for i in range(cfg.seq_len):
        wait = 0.0

        if len(fifo) >= N:
            fifo.pop(0)
            evictions += 1

            # Submit eviction to pipeline: if full, wait
            while len(completions) >= W:
                # Wait for earliest completion
                next_done = min(completions)
                if next_done > wall:
                    wait += next_done - wall
                    wall = next_done
                completions = [c for c in completions if c > wall]

            # Submit: completion at (wall + xfer)
            completions.append(wall + xfer)

        fifo.append(i)

        # Compute
        wall += comp

        # Clean up completed evictions
        completions = [c for c in completions if c > wall]

        steps.append(StepRec(i, len(fifo), evictions, wait, wall,
                             "eviction" if wait > 0 else "compute"))

    # Drain remaining evictions at end
    while completions:
        next_done = min(completions)
        if next_done > wall:
            wait = next_done - wall
            wall = next_done
        completions = [c for c in completions if c > wall]

    return steps


# ===================================================================
# Sweep
# ===================================================================

@dataclass
class SweepRec:
    latency_ms: float
    window: int
    mem_mb: int
    demand_s: float
    prefetch_s: float
    speedup: float


def run_sweep():
    results = []
    base = dict(num_layers=32, num_heads=32, head_dim=128,
                seq_len=4096, local_memory=512*1024*1024,
                latency_ms=50.0, bandwidth_mbps=500.0, prefetch_window=16)

    for lat in [5, 10, 20, 50, 100, 200]:
        p = dict(base); p['latency_ms'] = float(lat)
        c = SimConfig(**p)
        d, pf = simulate_demand(c), simulate_prefetch(c)
        results.append(SweepRec(lat, 16, 512,
                                d[-1].wall_ms/1000, pf[-1].wall_ms/1000,
                                d[-1].wall_ms/pf[-1].wall_ms))

    for w in [1, 2, 4, 8, 16, 32, 64]:
        p = dict(base); p['prefetch_window'] = w
        c = SimConfig(**p)
        d, pf = simulate_demand(c), simulate_prefetch(c)
        results.append(SweepRec(50, w, 512,
                                d[-1].wall_ms/1000, pf[-1].wall_ms/1000,
                                d[-1].wall_ms/pf[-1].wall_ms))

    for mb in [128, 256, 512, 1024, 2048]:
        p = dict(base); p['local_memory'] = mb * 1024 * 1024
        c = SimConfig(**p)
        d, pf = simulate_demand(c), simulate_prefetch(c)
        results.append(SweepRec(50, 16, mb,
                                d[-1].wall_ms/1000, pf[-1].wall_ms/1000,
                                d[-1].wall_ms/pf[-1].wall_ms))

    return results


# ===================================================================
# Analytical model for verification
# ===================================================================

def analytical_speedup(cfg: SimConfig) -> float:
    """Theoretical speedup under ideal pipelining."""
    S = cfg.seq_len
    N_evict = max(0, S - cfg.local_slots)
    ideal_prefetch = max(S * cfg.compute_ms, N_evict * cfg.xfer_ms / cfg.prefetch_window)
    demand = S * cfg.compute_ms + N_evict * cfg.xfer_ms
    return demand / ideal_prefetch if ideal_prefetch > 0 else 1.0


# ===================================================================
# Main
# ===================================================================

if __name__ == "__main__":
    cfg = SimConfig(seq_len=2048, local_memory=256*1024*1024)
    print(f"KV/token:     {cfg.kv_bpt/1024:.1f} KB")
    print(f"Local slots:  {cfg.local_slots}")
    print(f"Transfer:     {cfg.xfer_ms:.1f} ms  (1 token)")
    print(f"Pipeline cap: {cfg.prefetch_window} slots")
    print(f"Depth needed: {cfg.xfer_ms/cfg.compute_ms:.1f}")
    print(f"Latency comp: {cfg.latency_ms:.0f} ms  BW: {cfg.bandwidth_mbps:.0f} Mbps")
    print()

    d = simulate_demand(cfg)
    pf = simulate_prefetch(cfg)
    print(f"Demand:   {d[-1].wall_ms/1000:.1f}s  (evictions={d[-1].evictions_done})")
    print(f"Prefetch: {pf[-1].wall_ms/1000:.1f}s  (evictions={pf[-1].evictions_done})")
    print(f"Speedup:  {d[-1].wall_ms/max(pf[-1].wall_ms, 0.001):.2f}x")
    a = analytical_speedup(cfg)
    print(f"Analytical ideal: {a:.2f}x")
    print()

    sw = run_sweep()
    print(f"Sweep: {len(sw)} pts, max speedup={max(s.speedup for s in sw):.2f}x")
    print()
    print("--- Latency sweep ---")
    for s in [s for s in sw if s.window == 16 and s.mem_mb == 512]:
        print(f"  lat={s.latency_ms:>4}ms  D={s.demand_s:>6.0f}s  PF={s.prefetch_s:>6.0f}s  {s.speedup:.2f}x")
    print()
    print("--- Window sweep ---")
    for s in [s for s in sw if abs(s.latency_ms - 50) < 0.1 and s.mem_mb == 512]:
        print(f"  w={s.window:>2}  D={s.demand_s:>6.0f}s  PF={s.prefetch_s:>6.0f}s  {s.speedup:.2f}x")
    print()
    print("--- Memory sweep ---")
    for s in [s for s in sw if abs(s.latency_ms - 50) < 0.1 and s.window == 16]:
        print(f"  mem={s.mem_mb:>4}mb  D={s.demand_s:>6.0f}s  PF={s.prefetch_s:>6.0f}s  {s.speedup:.2f}x")
