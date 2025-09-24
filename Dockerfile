FROM python:3.10
COPY --from=ghcr.io/astral-sh/uv:0.7.22 /uv /uvx /bin/

WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

ADD . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

ENV PATH="/app/.venv/bin:$PATH"

# CMD ["uv", "run", "voice-agent"]
CMD ["/app/.venv/bin/voice-agent"]

###############################

# RUN pip install uv
# RUN --mount=source=dist,target=/dist uv pip install --no-cache --system /dist/*.whl
# WORKDIR /app
# ENV TERM=xterm
# EXPOSE 8000
# CMD voice-agent
