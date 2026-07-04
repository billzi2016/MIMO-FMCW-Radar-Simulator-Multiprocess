# 使用 slim Python 镜像，足够运行当前纯 Python 仿真和示例绘图依赖。
FROM python:3.11-slim

# 容器内统一工作目录，后续 COPY、运行命令都以这里为基准。
WORKDIR /app

# 先复制依赖文件再安装，方便 Docker 利用缓存：源码变动时不必重复安装依赖。
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 复制完整仓库。当前示例需要 `src/`、`examples/meshes/` 等目录。
COPY . /app

# 让 Python 在未安装 editable package 的情况下也能找到 src-layout 包。
ENV PYTHONPATH=/app/src

# 默认运行最小 box mesh 示例，输出 NPZ 到 examples/output/。
# 这个命令用于快速验证容器环境是否能跑通仿真链路。
CMD ["python", "-m", "mimo_fmcw_radar_simulator_multiprocess", "--mesh", "examples/meshes/box.obj", "--output", "examples/output/docker_run.npz"]
