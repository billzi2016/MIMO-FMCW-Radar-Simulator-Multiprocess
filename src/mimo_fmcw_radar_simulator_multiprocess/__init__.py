"""MIMO FMCW 雷达仿真器包入口。

这个包对外暴露最常用的五个对象/函数：
雷达配置、目标运动、网格加载、RDC 合成和 FFT 后处理。更底层的几何、
可见性和散射模型仍可直接 import，但默认入口保持简洁。

设计意图：
- 用户做脚本集成时，可以直接从包根导入核心 API。
- 内部模块仍保持拆分，便于分别理解雷达参数、mesh 加载、信号合成和 FFT。
- `__all__` 明确告诉维护者哪些对象属于稳定的公开入口。
"""

from .fft_pipeline import run_fft_pipeline
from .mesh_loader import load_mesh
from .radar_model import RadarConfig, TargetMotion
from .signal_synth import simulate_rdc

__all__ = [
    # 雷达与目标配置。
    "RadarConfig",
    "TargetMotion",
    # mesh 输入与仿真主链路。
    "load_mesh",
    "simulate_rdc",
    "run_fft_pipeline",
]
