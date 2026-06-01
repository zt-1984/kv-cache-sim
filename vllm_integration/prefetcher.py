# -*- coding: utf-8 -*-
"""
AsyncPrefetcher - 预取引擎,集成到 vLLM 的 Worker.schedule 中。

核心逻辑:在每个 decoding step 中,计算引擎预测下一个将被
驱逐的 block,提前发起 fetch.预测基于 FIFO 队列顺序:
最早生成的 block 最早被驱逐。

vLLM 集成点: 在 Worker.execute_model 的每步末尾调用
prefetch.step().
"""

import logging
from collections import deque
from typing import Set, Dict
from .config import OffloadConfig
from .network import WifiTransport

logger = logging.getLogger(__name__)


class AsyncPrefetcher:
    """异步预取流水线引擎.
    
    用法 (在 vLLM 的 LLMEngine 中):
    
        offloader = KVCacheOffloader(config, transport)
        scheduler.attach_offloader(offloader)
        
        # 在每个 decoding step 之后:
        offloader.prefetcher.step(current_step, active_blocks)
    """
    
    def __init__(self, config: OffloadConfig, transport: WifiTransport):
        self.config = config
        self.transport = transport
        self.window = config.prefetch_window
        
        # 当前正在传输中的请求
        self._inflight: Dict[int, float] = {}  # block_id -> expected_finish_time
        
        # 已知在远端的 block 集合
        self._remote_blocks: Set[int] = set()
        
        # 本地的 FIFO 队列 (用于预测驱逐顺序)
        self._local_fifo: deque = deque(maxlen=config.local_slots + 64)
        
        logger.info(f"Prefetcher initialized: window={self.window}")
    
    def record_allocation(self, block_id: int):
        """BlockManager 分配新 block 时调用"""
        self._local_fifo.append(block_id)
    
    def record_eviction(self, block_id: int):
        """BlockManager 驱逐 block 时调用"""
        self._remote_blocks.add(block_id)
        # 从 FIFO 中移除
        if block_id in self._local_fifo:
            self._local_fifo.remove(block_id)
    
    def step(self, current_step: int):
        """每步末尾调用:清空已完成传输,发起预取请求.
        
        预取目标 = 当前 FIFO 中最旧的 block (即将被驱逐).
        提前 self.window 步发起传输.
        """
        # 1. 清空已完成传输
        now = time.time()
        done = [bid for bid, eta in self._inflight.items() if eta <= now]
        for bid in done:
            self._remote_blocks.discard(bid)
            del self._inflight[bid]
        
        # 2. 预测将被驱逐的 block,发起预取
        if len(self._local_fifo) >= self._local_fifo.maxlen:
            # 即将被驱逐的是 FIFO 中最旧的 block
            for offset in range(1, self.window + 1):
                if offset <= len(self._local_fifo):
                    target = self._local_fifo[offset - 1]
                    if target in self._remote_blocks and target not in self._inflight:
                        # 发起预取:后台线程传输
                        t = self.transport.transfer_time_ms(
                            self.config.kv_per_token_bytes
                        ) / 1000.0
                        self._inflight[target] = time.time() + t
                        logger.debug(f"Prefetch block {target}, "
                                     f"ETA in {t*1000:.0f}ms")
        
        # 3. 检查关键流水线条件
        if self.window * 30 < self.config.transfer_time_ms:
            logger.warning(
                f"Prefetch window too small: "
                f"{self.window} x 30ms = {self.window*30}ms < "
                f"{self.config.transfer_time_ms:.0f}ms. "
                f"Consider increasing prefetch_window to at least "
                f"{int(self.config.transfer_time_ms/30)+1}."
            )


import time  # noqa: needed for timestamp
