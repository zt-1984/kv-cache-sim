#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test vLLM offloader integration (no GPU needed)."""
import sys, os
pkg = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, pkg)
from vllm_integration.config import OffloadConfig
from vllm_integration.offloader import KVCacheOffloader

def run():
    cfg = OffloadConfig(local_memory_mb=512, prefetch_window=16)
    off = KVCacheOffloader(cfg)
    assert off.config.local_slots == 1024
    for bid in range(1024): off.on_allocate(bid)
    assert len(off._local_blocks) == 1024
    for bid in range(100, 200): off.on_swap_out(bid)
    assert len(off._remote_blocks) == 100
    for step in range(10): off.on_step_complete()
    assert off.get_stats()["steps"] == 10
    off.on_swap_in(150)
    assert off._total_fetches == 1
    stats = off.get_stats()
    print("[PASS] All tests passed")
    print(f"Stats: {stats}")
    print(f"Critical window: {int(cfg.transfer_time_ms/30)+1}")
    return 0

if __name__ == '__main__': sys.exit(run())