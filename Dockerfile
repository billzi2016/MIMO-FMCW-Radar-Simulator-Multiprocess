FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

ENV PYTHONPATH=/app/src

CMD ["python", "-m", "mimo_fmcw_radar_simulator_multiprocess", "--mesh", "examples/meshes/box.obj", "--output", "examples/output/docker_run.npz"]
