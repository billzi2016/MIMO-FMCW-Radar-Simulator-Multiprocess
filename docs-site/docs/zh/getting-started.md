# 快速开始

## 安装

在仓库根目录执行：

```bash
pip install -e .
```

## 运行 Box 示例

```bash
python -m mimo_fmcw_radar_simulator_multiprocess \
  --mesh examples/meshes/box.obj \
  --output examples/output/box_run.npz
```

## 运行人体 Mesh 示例

```bash
python -m mimo_fmcw_radar_simulator_multiprocess \
  --mesh examples/meshes/Thanh.glb \
  --max-faces 1200 \
  --num-chirps 16 \
  --output examples/output/thanh_run.npz
```

## 绘制输出结果

```bash
python examples/plot/plot_thanh_run.py \
  --input examples/output/thanh_run.npz
```

绘图脚本会生成距离-速度、距离-角度、速度-角度、距离-Chirp 和总览热力图。
