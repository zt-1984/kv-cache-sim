# vllm_integration - vLLM KV Cache Offloading Extension
# 将异步预取卸载插件到 vLLM 的 BlockManager 中
from .config import OffloadConfig
from .network import WifiTransport
from .prefetcher import AsyncPrefetcher
from .offloader import KVCacheOffloader
__version__ = "1.0.0"
