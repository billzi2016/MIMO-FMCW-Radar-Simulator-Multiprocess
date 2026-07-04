# FMCW 雷达是什么

FMCW 是 **frequency-modulated continuous wave**，中文通常叫调频连续波雷达。

它不是发一个很短的脉冲，而是持续发射一个频率随时间变化的信号。毫米波雷达里最常见的是重复发送线性扫频信号，也就是 **chirp**。

对初学者来说，最重要的一句话是：FMCW 雷达不是直接拿秒表去量回波延迟，而是把时间延迟转换成频率差。频率差可以很方便地从采样数据里用 FFT 找出来，所以 FMCW 很适合小型毫米波雷达。

## Chirp

一个 chirp 会在很短时间内从一个频率扫到另一个频率。

线性 chirp 可以写成：

```text
frequency(t) = start_frequency + slope * t
```

调频斜率是：

```text
slope = bandwidth / chirp_duration
```

在本项目中，`RadarConfig.slope_hz_per_s` 计算的就是这个值。

带宽决定距离分辨率。带宽越大，越容易区分距离很接近的两个目标。chirp 时长和 ADC 采样点数决定一个扫频里有多少 fast-time 采样点。

在代码里，这些值都在 `RadarConfig` 中：

```python
bandwidth_hz
chirp_duration_s
num_adc_samples
```

它们不是普通配置数字，而是在定义模拟雷达的物理采样网格。

## Beat Frequency

目标回波会延迟返回。因为发射 chirp 的频率一直在变，所以“当前发射信号”和“延迟回来的接收信号”之间会有一个频率差。

FMCW 雷达会把发射信号和接收信号混频，得到一个较低频率的信号，通常叫 **beat signal**。

对于简单目标，beat frequency 和往返延迟近似成正比：

```text
beat_frequency = slope * round_trip_delay
```

这就是 FMCW 雷达能够估计距离的核心原因。

初学者可以这样理解：

1. 雷达正在向上扫频。
2. 目标回波是之前某一时刻发出去的信号的延迟版本。
3. 延迟回波和当前发射信号相比，会出现一个频率差。
4. 目标越远，延迟越大。
5. 延迟越大，beat frequency 越大。

所以混频之后，距离信息变成了频率信息。接下来 FFT 就可以把这个频率找出来。

## Fast Time 和 Range FFT

在一个 chirp 内，ADC 会沿 fast time 采样。

Range FFT 就是在 fast time 维度上做 FFT。FFT 里的峰值对应 beat frequency，而 beat frequency 对应目标距离。

在本项目中：

- fast-time 维度：`num_adc_samples`
- 距离处理：沿 axis `0` 做 FFT

模拟器把这个维度放在原始数据立方体的第一个轴：

```text
rdc[adc_sample, chirp, virtual_channel]
```

当 `fft_pipeline.py` 执行：

```python
range_fft = np.fft.fft(rdc, axis=0)
```

它实际上是在问：“每个 chirp 内有哪些 beat frequency？”这些频率随后会被解释成距离 bin。

## Slow Time 和 Doppler FFT

雷达会重复发送多个 chirp。chirp 序列构成 slow time。

如果目标在运动，它的回波相位会在 chirp 与 chirp 之间变化。Doppler FFT 沿 slow time 做，用来估计速度。

在本项目中：

- slow-time 维度：`num_chirps`
- 速度处理：沿 axis `1` 做 FFT

本项目使用简单的恒速目标模型。目标位置按下面公式变化：

```text
position = initial_position + velocity * slow_time
```

这种运动会让每个 chirp 的距离和相位发生变化。Doppler FFT 读取的就是这些跨 chirp 的相位变化。

如果只有一个 chirp，就没有 slow-time 序列，也就很难估计速度。这就是 `num_chirps` 很重要的原因。

## MIMO 通道和 Angle FFT

MIMO 雷达使用多个发射天线和接收天线，组合出虚拟天线阵列。

同一个目标在不同虚拟通道上的相位略有差异。沿通道维度做 FFT，可以得到角度估计。

在本项目中：

- 通道维度：`num_tx * num_rx`
- 角度处理：沿 axis `2` 做 FFT

模拟器构造了一个简化虚拟线阵：

- RX 阵元按半波长排列。
- TX 阵元拉开距离，使 TX/RX 组合形成更宽的虚拟孔径。
- 每一个 TX/RX 组合对应一个虚拟通道。

这个模型是简化的，但足够说明为什么通道相位里包含角度信息。

## FMCW 在代码里对应哪里

FMCW 公式最直接体现在 `signal_synth.py` 的 `_synthesize_channel()` 中。

这个函数会计算：

- 发射天线到散射点的距离
- 散射点到接收天线的距离
- 往返延迟
- `slope * delay` 得到 beat frequency
- 由载频和 chirp 延迟项得到静态相位
- fast-time 上的复指数信号

概念上最关键的是：

```text
phase = static_phase + 2π * beat_frequency * fast_time
```

也就是说，每个散射点都会在 ADC 采样维度上贡献一个复正弦波。这个正弦波的频率代表距离，跨 chirp 和跨通道的相位变化又支持速度和角度估计。

## 本项目简化了什么

这个项目为了可读性和教学目的，省略了很多工程雷达细节：

- 没有热噪声
- 没有 ADC 量化
- 没有泄漏消除
- 没有 CFAR 检测
- 没有 MUSIC 等高分辨率角度估计
- 没有多径模型
- 没有复杂电磁材料模型

它的重点是讲清楚主链路：延迟变成距离，相位变化变成速度，通道相位差变成角度。

## 初学者推荐阅读顺序

如果你刚接触 FMCW 雷达，建议按这个顺序看代码：

1. `radar_model.py`：先理解带宽、chirp 时长、ADC 采样点、chirp 数、TX/RX 数。
2. `signal_synth.py`：看距离如何变成延迟，延迟如何变成 beat frequency。
3. `fft_pipeline.py`：看三个维度如何变成距离、速度和角度。
4. `examples/plot/plot_thanh_run.py`：看 FFT 输出如何变成热力图。

这个顺序和物理链路一致：先定义雷达，再合成信号，再变换信号，最后可视化。
