# Build stage
FROM python:3.13-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml README.md ./
COPY src ./src

# Build the package
RUN uv build --wheel

# Runtime stage
FROM python:3.13-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash lazyecs

# Set working directory
WORKDIR /app

# Copy wheel from builder
COPY --from=builder /app/dist/*.whl /tmp/

# Install the package
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

# Switch to non-root user
USER lazyecs

# Set entrypoint
ENTRYPOINT ["lazy-ecs"]
CMD ["--help"]