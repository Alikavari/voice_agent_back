FROM python:3.12
RUN pip install uv
RUN --mount=source=dist,target=/dist uv pip install --no-cache --system /dist/*.whl
WORKDIR /app
ENV TERM=xterm
EXPOSE 8000
CMD voice-agent
