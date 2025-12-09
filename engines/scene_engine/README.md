# Scene Engine

FastAPI service for building 3-D scene JSON from grid/box inputs.

## Run locally

```bash
docker build -t scene-engine:dev engines/scene_engine
docker run -p 8080:8080 scene-engine:dev
```

Endpoints:
- `GET /health`
- `POST /scene/build`
