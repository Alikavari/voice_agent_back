## Build binary

```bash
uv build --wheel --clean
```

## Creating Docker image

```bash
docker build . --tag your-image-name
```

E.g:
```
docker build . --tag ghcr.io/mohsennz/voice-agent-backend:latest
```
