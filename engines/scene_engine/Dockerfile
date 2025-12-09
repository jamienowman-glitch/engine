# Scene Engine v1 container
FROM python:3.12-slim AS base
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS runtime
WORKDIR /app
COPY engines ./engines
EXPOSE 8080
CMD ["uvicorn", "engines.scene_engine.service.server:app", "--host", "0.0.0.0", "--port", "8080"]
