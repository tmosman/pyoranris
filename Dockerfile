# Optional image for headless CI / backend experiments.
# Prefer host GUI: pip install -e ".[gui]" && pyoranris run
FROM python:3.10-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY configs ./configs
RUN pip install --no-cache-dir -e ".[dev]"
ENV PYTHONUNBUFFERED=1
CMD ["pyoranris", "run", "-c", "configs/offline_sim.yaml", "--headless"]
