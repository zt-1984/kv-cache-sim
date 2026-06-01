# vLLM KV Cache Offloader - 部署指南

## 前置条件
- NVIDIA GPU (A100-80G / 4090 及以上)
- CUDA 12.1+, vLLM >= 0.4.0, PyTorch >= 2.1.0

## 集成步骤 (共 19 行代码修改)

### 1. 复制本目录到 vLLM 源码
`ash
cp -r vllm_integration /path/to/vllm/
`

### 2. 修改 vllm/engine/llm_engine.py (6 行)
`python
# 在 __init__ 末尾添加:
from vllm_integration import KVCacheOffloader, OffloadConfig
self.offloader = KVCacheOffloader(
    OffloadConfig(
        remote_host="192.168.1.100",
        prefetch_window=8,
    )
)
self.worker.offloader = self.offloader
`

### 3. 修改 vllm/worker/worker.py (5 行)
`python
# 在 execute_model 末尾:
if hasattr(self, 'offloader') and self.offloader:
    self.offloader.on_step_complete()
`

### 4. 修改 vllm/core/block_manager.py (8 行)
`python
# allocate() 中:
if hasattr(self, 'offloader') and self.offloader:
    self.offloader.on_allocate(block_id)

# free() 中:
if hasattr(self, 'offloader') and self.offloader:
    self.offloader.on_free(block_id)

# swap_out() 中 - 替换 CPU swap 为远端卸载:
if hasattr(self, 'offloader') and self.offloader:
    self.offloader.on_swap_out(block_id)
    return  # 跳过原 CPU swap

# swap_in() 中 - 替换 CPU swap-in 为远端取回:
if hasattr(self, 'offloader') and self.offloader:
    data = self.offloader.on_swap_in(block_id)
    if data is not None:
        return data
`

## 验证
`ash
# 无 GPU 单元测试
python -m vllm_integration.test_offloader

# 实际推理
python examples/run_with_offload.py --model meta-llama/Llama-2-7b-hf
`

## 设计原理
参考 simulation/kv_cache_sim.py 的数学模型。核心公式:
- 加速比 = T_demand / T_prefetch
- 临界窗口 W = ceil(t_xfer / t_comp)
- 默认: t_comp=30ms, t_xfer=108.8ms -> W_min=4, 加速比=3.72x
