# 核心模块

这一页按代码文件解释项目结构。它不是简单列目录，而是说明每个模块在雷达仿真链路里的位置。

可以先记住一条主线：

```text
radar_model -> mesh_loader / geometry -> visibility -> scatter_model -> signal_synth -> fft_pipeline
```

`main.py` 负责把这些模块串起来，`multiprocess_engine.py` 负责让信号合成阶段并行执行。

## `radar_model.py`

定义雷达配置、派生物理参数、天线位置、虚拟通道和目标运动。

它主要包含两个数据类：

- `RadarConfig`
- `TargetMotion`

`RadarConfig` 描述雷达本身，例如载频、带宽、chirp 时长、ADC 采样点数、chirp 数、TX/RX 数。它还会根据这些基础参数计算派生量：

- 波长
- FMCW 调频斜率
- fast-time 采样轴
- slow-time chirp 轴
- Tx/Rx 阵元位置
- MIMO 虚拟通道位置

`TargetMotion` 描述目标怎么运动，包括初始位置、速度、姿态角和整体反射率。

初学者可以把这个文件理解成“仿真参数中心”。后续所有模块都依赖它，但它自己不生成雷达信号。

## `mesh_loader.py`

读取 `OBJ`、`STL` 和 `GLB` mesh，并转换为内部三角网格表示。

这个文件负责把不同 3D 文件格式统一成项目内部的 `TriangleMesh`。

为什么要统一？因为后面的可见性判断、散射建模和信号合成都只关心三件事：

- 顶点坐标
- 三角面索引
- 三角面几何关系

不同格式的纹理、材质、动画信息都不会进入雷达模型。这样后续代码就不用关心输入到底来自 OBJ、STL 还是 GLB。

## `geometry.py`

提供三角面中心、法向、面积、欧拉角旋转、刚体变换和射线三角面相交判断。

这是项目的几何工具箱。它不理解雷达，也不理解 FMCW，只提供纯三维几何计算。

重要函数包括：

- `triangle_centers()`：计算三角面中心，用作散射点位置。
- `triangle_normals()`：计算法向，用于判断面是否朝向雷达。
- `triangle_areas()`：计算面积，用于估计散射强度。
- `euler_rotation_matrix()`：把欧拉角变成旋转矩阵。
- `transform_vertices()`：对 mesh 顶点做旋转和平移。
- `ray_triangle_intersection()`：判断射线是否被三角面挡住。

可见性判断和散射模型都建立在这些基础几何函数上。

## `visibility.py`

按朝向和视线遮挡筛选三角面。

这个模块回答一个核心问题：雷达到底能不能看到某个面？

它先做朝向判断：如果一个三角面的法向背向雷达，就认为它不会产生直接有效回波。

然后做遮挡判断：从雷达相位中心向三角面中心发射射线，如果这条线先撞到别的三角面，说明目标面被遮挡。

这一步不是高性能实现，但逻辑非常直观。它适合教学，也适合检查“哪些面参与了雷达回波”。

## `scatter_model.py`

将可见三角面转换为简化散射点。

经过可见性筛选后，项目不再直接处理完整三角面，而是把每个面近似成一个散射点。

散射点有两个核心属性：

- `centers_m`：散射点位置
- `strengths`：散射强度

强度近似由三角面面积、入射角和整体反射率共同决定。这个模型不追求完整电磁精度，而是让“几何如何影响雷达信号”变得清楚。

## `signal_synth.py`

在 ADC 采样点、chirp 和 MIMO 虚拟通道三个维度上合成原始雷达数据立方体。

这是项目的核心计算模块。

它做的事可以拆成三层：

1. 对每个 chirp 更新目标位置。
2. 对当前姿态下的 mesh 做可见性和散射点构造。
3. 对每个 TX/RX 通道合成 FMCW 复数回波。

最重要的输出是 `rdc`：

```text
num_adc_samples x num_chirps x (num_tx * num_rx)
```

这个数据立方体还不是最终结果，而是 FFT 前的原始雷达采样。

## `fft_pipeline.py`

执行距离、速度和角度 FFT，并输出可视化所需的 map 和坐标轴。

这个模块负责把原始 `rdc` 解释成人能理解的雷达结果：

- 沿 ADC 采样点做 FFT，得到距离信息。
- 沿 chirp 维度做 FFT，得到速度信息。
- 沿虚拟通道维度做 FFT，得到角度信息。

它还会生成坐标轴：

- `range_axis_m`
- `doppler_axis_m_s`
- `angle_axis_deg`

这些坐标轴让热力图不只是数组，而是能对应真实物理单位。

## `multiprocess_engine.py`

将 chirp 拆成多个工作块，并用多进程执行耗时的信号合成阶段。

这个模块不理解雷达物理，只负责并行调度。

它提供三个工具：

- `default_worker_count()`：默认使用一半 CPU 核心。
- `split_indices()`：把 chirp 范围切成连续块。
- `parallel_map()`：根据 worker 数决定串行还是多进程执行。

为什么按 chirp 拆？因为每个 chirp 的信号合成基本独立，只要最后按原顺序写回 `rdc` 就可以。

## `main.py`

`main.py` 是命令行入口，负责把所有模块串起来。

它的流程是：

1. 解析命令行参数。
2. 创建 `RadarConfig` 和 `TargetMotion`。
3. 加载 mesh。
4. 可选地按 `--max-faces` 降低面数。
5. 调用 `simulate_rdc()` 合成原始雷达数据。
6. 调用 `run_fft_pipeline()` 做 FFT。
7. 保存 `.npz` 输出。

这个文件适合初学者第一步阅读，因为它展示了整个项目如何运行。

## `examples/plot/plot_thanh_run.py`

这个脚本负责把 `.npz` 输出画成 PNG 热力图。

它不会改变仿真结果，只是把数组可视化。它生成的图包括：

- Range-Doppler
- Range-Angle
- Doppler-Angle
- Range-Chirp
- Summary heatmaps

如果你想确认仿真结果是否合理，通常先看这个脚本生成的图。
