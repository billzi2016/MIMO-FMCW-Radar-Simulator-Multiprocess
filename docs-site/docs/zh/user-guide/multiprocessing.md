# 多进程加速原理

这个模拟器最慢的部分是原始雷达信号合成。它需要对许多 chirp、虚拟通道和可见散射点重复做类似计算。

多进程加速的思路是：沿 chirp 维度拆分任务，同时保持物理模型不变。

## 为什么按 Chirp 拆分

只要雷达配置、目标运动和 mesh 已知，每个 chirp 的信号都可以独立合成。

对第 `k` 个 chirp，模拟器会：

1. 计算 slow-time 对应的目标位置。
2. 变换 mesh。
3. 提取可见三角面。
4. 构造散射点。
5. 为所有 TX/RX 通道合成该 chirp 的信号。

这个过程不依赖其他 chirp 的中间结果，所以 chirp 是天然适合并行的单位。

## 任务切分

`multiprocess_engine.split_indices()` 会把 chirp 索引范围切成连续块。

例如：

```text
num_chirps = 64
workers = 4

blocks:
0-16
16-32
32-48
48-64
```

每个块会变成一个 `_BlockTask`。

## Worker 做什么

每个 worker 执行 `signal_synth.py` 里的 `_simulate_block()`。

一个 block task 包含：

- 起始 chirp index
- 结束 chirp index
- mesh
- 雷达配置
- 目标运动配置

worker 返回：

```text
(start, stop, block)
```

其中 `block` 的形状是：

```text
num_adc_samples x block_num_chirps x (num_tx * num_rx)
```

主进程再把它写回最终 RDC 数组的 `rdc[:, start:stop, :]` 位置。

## 为什么用进程而不是线程

Python 线程会受到 GIL 影响。这个项目虽然使用 numpy，但外层还有 Python 循环、可见性判断和逐通道调度。

使用 `ProcessPoolExecutor` 可以让每个 worker 运行在独立 Python 进程里，避开外层 Python 调度的 GIL 瓶颈，让 CPU 密集型 block 并行执行。

## 为什么默认只用一半 CPU

`default_worker_count()` 返回：

```text
max(1, os.cpu_count() // 2)
```

默认只用一半 CPU，是因为雷达仿真不只吃计算，也会占用内存带宽。尤其在笔记本或桌面机器上，把所有核心打满不一定更快，也会影响其他任务。

用户可以手动指定：

```bash
python -m mimo_fmcw_radar_simulator_multiprocess --workers 8
```

## 多进程不会改变什么

多进程只改变执行方式，不改变：

- 雷达参数
- 目标运动
- 可见性逻辑
- 散射强度
- FMCW 相位公式
- FFT 处理方式

因此相同输入下，多进程运行和串行运行在概念上应该得到相同结果。

## 当前限制

当前可见性阶段会直接用射线和完整 mesh 的三角面做相交测试。这个方法容易理解，但大 mesh 上开销很高。

未来更有效的加速方向是加入空间加速结构，例如：

- BVH
- KD-tree
- uniform grid

这样可以在信号合成之前先降低可见性判断成本。

## 串行版本和多进程版本的区别

串行版本可以理解成：

```text
for chirp in all_chirps:
    模拟这个 chirp
    写入 RDC
```

多进程版本保留同样逻辑，只是把 chirp 分成块：

```text
worker 1: chirps 0-15
worker 2: chirps 16-31
worker 3: chirps 32-47
worker 4: chirps 48-63
```

每个 worker 生成一个局部数据立方体。主进程再把局部结果插入最终立方体的对应 slow-time 位置。

这种方式成立，是因为不同 chirp 块之间不重叠。没有两个 worker 会写同一段输出。

## 数据复制成本

多进程不是免费的。Python 需要把任务数据发送给 worker 进程，再把结果数组收回来。

任务里包含 mesh、雷达配置和目标配置。如果 mesh 很大，复制或序列化这些数据也会有成本。所以只有当每个 block 的计算量足够大时，多进程收益才明显。

如果 mesh 很小，或者 `num_chirps` 很少，单进程可能一样快，甚至更快。

## 什么时候会加速

多进程更适合这些情况：

- `num_chirps` 较大
- mesh 面数较多
- 可见性判断很耗时
- 需要合成很多虚拟通道
- 每个 worker 分到的计算量足够覆盖进程开销

这些情况可能加速不明显：

- 输入 mesh 很小
- 只模拟很少 chirp
- 机器已经被内存带宽限制
- worker 太多，互相抢 CPU 和内存资源

## 为什么结果合并是安全的

每个 worker 返回自己的 chirp 范围：

```text
(start, stop, block)
```

主进程写入：

```python
rdc[:, start:stop, :] = block
```

这是安全的，因为每个 block 对应不同 chirp 区间。worker 不会直接修改最终 `rdc` 数组，只会返回独立结果。

## 实用调参建议

初学者可以按这个规则调：

1. 先用默认 worker 数。
2. 如果机器还很空闲，可以尝试增大 `--workers`。
3. 如果运行反而变慢，就减少 worker。
4. 如果 mesh 太大，优先试 `--max-faces`，不要只靠加 worker。

很多时候，`--max-faces` 比 worker 数更关键，因为直接可见性判断可能是最耗时的部分。

## 未来加速方向

当前多进程是粗粒度加速：它并行 chirp 块，但没有改变可见性判断的算法复杂度。

未来高性能版本可以结合：

- BVH 或空间索引用于射线三角面查询
- 向量化散射点信号合成
- 可选 GPU 加速
- 如果目标姿态变化慢，可以缓存可见性结果

当前设计把多进程隔离在 `multiprocess_engine.py`，就是为了以后还能替换或升级加速策略。
