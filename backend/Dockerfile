FROM python:3.12-slim

WORKDIR /app

# Install uv for fast, reproducible installs from the lockfile.
COPY --from=ghcr.io/astral-sh/uv:0.5.4 /uv /bin/uv

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --frozen || uv sync --no-dev

COPY . .

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
