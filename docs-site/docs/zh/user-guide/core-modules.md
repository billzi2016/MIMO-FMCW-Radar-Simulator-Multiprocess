# 核心模块

## `radar_model.py`

定义雷达配置、派生物理参数、天线位置、虚拟通道和目标运动。

## `mesh_loader.py`

读取 `OBJ`、`STL` 和 `GLB` mesh，并转换为内部三角网格表示。

## `geometry.py`

提供三角面中心、法向、面积、欧拉角旋转、刚体变换和射线三角面相交判断。

## `visibility.py`

按朝向和视线遮挡筛选三角面。

## `scatter_model.py`

将可见三角面转换为简化散射点。

## `signal_synth.py`

在 ADC 采样点、chirp 和 MIMO 虚拟通道三个维度上合成原始雷达数据立方体。

## `fft_pipeline.py`

执行距离、速度和角度 FFT，并输出可视化所需的 map 和坐标轴。

## `multiprocess_engine.py`

将 chirp 拆成多个工作块，并用多进程执行耗时的信号合成阶段。
