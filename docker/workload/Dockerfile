FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY baseline_lab /app/baseline_lab

RUN pip install --no-cache-dir .

ENTRYPOINT ["python", "-m", "baseline_lab.cli"]
