"""模块执行入口。

这个文件只做一件事：允许用户通过下面的方式启动命令行仿真：

```bash
python -m mimo_fmcw_radar_simulator_multiprocess
```

真正的参数解析和仿真流程都在 `main.py`，这里保持极薄入口，避免出现
两个命令行实现分叉。
"""

from .main import main


if __name__ == "__main__":
    # Python 以模块方式执行包时，会进入这里并转交给真正 CLI。
    main()
