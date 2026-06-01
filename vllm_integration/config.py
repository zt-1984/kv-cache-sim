# -*- coding: utf-8 -*-
"""
OffloadConfig - 暴露给 vLLM Engine 的配置接口。
在启动 vLLM 时通过 LLMEngine 的参数传入。
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class OffloadConfig:
    """KV Cache 卸载配置,用法:
    
    from vllm import LLM, SamplingParams
    from vllm_integration import OffloadConfig
    
    llm = LLM(
        model="meta-llama/Llama-2-7b-hf",
        offload_config=OffloadConfig(
            remote_host="192.168.1.100",
            prefetch_window=8,
            local_memory_mb=512,
        ),
    )
    
    原理: 每个 ViT/Decode step, vLLM 的 BlockManager
    会分配新的 KV block. 当 GPU 显存不足时,BlockManager
    自动触发 swap out. 本扩展将 swap out 目标从 CPU 
    改为远端 PC,并插入预取流水线.
    """
    
    # ---- 远端节点 ----
    remote_host: str = "192.168.1.100"
    remote_port: int = 12345
    remote_password: str = ""          # 可选,连接密码
    
    # ---- 卸载策略 ----
    local_memory_mb: int = 512         # 本地保留的 KV cache 上限(MB)
    prefetch_window: int = 16          # 流水线深度(W)
    prefetch_threshold: float = 0.75   # 本地占用超此比例开始预取
    
    # ---- 网络参数 ----
    network_latency_ms: float = 50.0   # 单向延迟(ms)
    network_bandwidth_mbps: float = 500.0  # Wi-Fi 带宽(Mbps)
    
    # ---- 调试 ----
    log_level: str = "INFO"            # DEBUG/INFO/WARNING
    dry_run: bool = False              # True = 只打日志,不传输
    
    def __post_init__(self):
        self._validate()
    
    def _validate(self):
        assert 0 < self.local_memory_mb < 1024 * 16, \
            f"local_memory_mb must be between 1 and 16384"
        assert 1 <= self.prefetch_window <= 256, \
            f"prefetch_window must be between 1 and 256"
        assert 0 < self.network_latency_ms < 10000
        assert 0 < self.network_bandwidth_mbps < 100000
    
    @property
    def kv_per_token_bytes(self) -> int:
        """7B 模型的 KV 每 token 大概字节数"""
        return 2 * 32 * 32 * 128 * 2  # 512 KB
    
    @property
    def local_slots(self) -> int:
        return int(self.local_memory_mb * 1024 * 1024
                   / self.kv_per_token_bytes)
    
    @property
    def transfer_time_ms(self) -> float:
        bits = self.kv_per_token_bytes * 8 * 1.05
        bw_ms = bits / (self.network_bandwidth_mbps * 1e6) * 1000
        return bw_ms + 2 * self.network_latency_ms
