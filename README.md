## Creating Docker image

```
rye build --wheel --clean
docker build . --tag your-image-name
```

E.g:
```
docker build . --tag ghcr.io/mohsennz/voice-agent-backend:latest
```
