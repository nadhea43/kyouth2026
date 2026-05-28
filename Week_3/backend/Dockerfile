FROM python:3.12-bookworm

# Copy uv package manager from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first (faster rebuilds)
# If only code changes, Docker skips reinstalling packages
COPY pyproject.toml uv.lock ./

# Install all dependencies
RUN uv sync --frozen

# Copy all source code
COPY . .

# Start backend on port 8001
ENTRYPOINT ["uv", "run", "uvicorn"]
CMD ["--app-dir", "src", "--host", "0.0.0.0", "--port", "8001", "app:app"]