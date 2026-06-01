# -*- coding: utf-8 -*-
"""KVCacheOffloader - vLLM BlockManager extension"""
import logging
from .config import OffloadConfig
from .network import WifiTransport
from .prefetcher import AsyncPrefetcher
logger = logging.getLogger(__name__)
class KVCacheOffloader:
    def __init__(self, config: OffloadConfig):
        self.config = config
        self.transport = WifiTransport(config.network_latency_ms, config.network_bandwidth_mbps, config.remote_host, config.remote_port)
        self.prefetcher = AsyncPrefetcher(config, self.transport)
        self._local_blocks = set()
        self._remote_blocks = set()
        self._step_count = 0
        self._total_evictions = 0
        self._total_fetches = 0
    def on_allocate(self, block_id):
        self._local_blocks.add(block_id)
        self.prefetcher.record_allocation(block_id)
    def on_free(self, block_id):
        self._local_blocks.discard(block_id)
        self._remote_blocks.discard(block_id)
    def on_swap_out(self, block_id):
        self._local_blocks.discard(block_id)
        self._remote_blocks.add(block_id)
        self._total_evictions += 1
        return self.transport.evict(block_id, b'x' * self.config.kv_per_token_bytes)
    def on_swap_in(self, block_id):
        if block_id in self._remote_blocks:
            self._remote_blocks.discard(block_id)
            self._local_blocks.add(block_id)
            self._total_fetches += 1
            return self.transport.fetch(block_id)
        return None
    def on_step_complete(self):
        self._step_count += 1
        self.prefetcher.step(self._step_count)
    def get_stats(self):
        return {'steps': self._step_count, 'local': len(self._local_blocks), 'remote': len(self._remote_blocks), 'evictions': self._total_evictions, 'fetches': self._total_fetches}
