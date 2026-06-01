# -*- coding: utf-8 -*-
"""
WifiTransport - 模拟远端 KV 页面的网络传输层。
生产环境替换为真实 socket 或 gRPC 调用。
"""

import threading
import time
import logging
from typing import Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TransferRequest:
    """一次网络传输请求"""
    block_id: int           # vLLM 的 Block ID
    data_size: int          # 字节数
    direction: str          # "evict" or "fetch"
    issued_at: float        # 发出时间戳
    completed_at: float = 0.0
    success: bool = False


class WifiTransport:
    """Wi-Fi 6 传输层.
    
    集成到 vLLM 中时,替换这里的模拟延时为 socket.send/recv.
    """
    
    def __init__(self, latency_ms: float, bandwidth_mbps: float,
                 remote_host: str = "localhost", remote_port: int = 12345):
        self.latency_s = latency_ms / 1000.0
        self.bandwidth_bps = bandwidth_mbps * 1e6
        self.remote_host = remote_host
        self.remote_port = remote_port
        self._stats = {"evictions": 0, "fetches": 0, "total_bytes": 0,
                       "total_time_ms": 0.0}
    
    def transfer_time_ms(self, data_size_bytes: int) -> float:
        """计算一次传输的耗时"""
        bits = data_size_bytes * 8 * 1.05  # 5% 协议开销
        bw_s = bits / self.bandwidth_bps
        return (bw_s + 2 * self.latency_s) * 1000  # ms
    
    def evict(self, block_id: int, data: bytes) -> TransferRequest:
        """将 KV block 写入远端 (卸载)"""
        req = TransferRequest(block_id, len(data), "evict", time.time())
        # ----- 生产环境替换为实际 socket 代码 -----
        # with socket.create_connection((self.remote_host, self.remote_port)) as sock:
        #     sock.sendall(data)
        #     ack = sock.recv(4)
        # -----------------------------------------
        t = self.transfer_time_ms(len(data)) / 1000
        time.sleep(t)  # 模拟延迟
        req.completed_at = time.time()
        req.success = True
        self._stats["evictions"] += 1
        self._stats["total_bytes"] += len(data)
        self._stats["total_time_ms"] += t * 1000
        return req
    
    def fetch(self, block_id: int) -> Optional[bytes]:
        """从远端取回 KV block"""
        req = TransferRequest(block_id, 0, "fetch", time.time())
        t = self.transfer_time_ms(self._estimate_block_size()) / 1000
        time.sleep(t)
        req.completed_at = time.time()
        req.success = True
        self._stats["fetches"] += 1
        return b"\\x00" * self._estimate_block_size()
    
    def _estimate_block_size(self) -> int:
        return 512 * 1024  # 512 KB per block
    
    @property
    def stats(self) -> dict:
        return dict(self._stats)
    
    def reset_stats(self):
        self._stats = {"evictions": 0, "fetches": 0,
                       "total_bytes": 0, "total_time_ms": 0.0}
