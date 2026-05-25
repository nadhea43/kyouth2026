# 1. Use the official lightweight Python image specified in your handout
FROM python:3.14.4-bookworm

# 2. Install 'uv' inside the container so we can manage dependencies
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 3. Set the working directory inside the container
WORKDIR /app

# 4. Copy package files first to leverage Docker's caching mechanism
COPY pyproject.toml uv.lock ./

# 5. Install the required dependencies using uv (without creating a virtual env inside docker)
RUN uv sync --frozen --no-cache

# 6. Copy the source code and templates into the container
COPY src/ ./src/

# 7. Configure entrypoint and runtime arguments to run Uvicorn via uv
ENTRYPOINT ["uv", "run", "uvicorn"]
CMD ["--app-dir", "src", "--host", "0.0.0.0", "app:app"]