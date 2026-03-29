# Build stage
FROM python:3.14-slim@sha256:fb83750094b46fd6b8adaa80f66e2302ecbe45d513f6cece637a841e1025b4ca as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.11.2@sha256:c4f5de312ee66d46810635ffc5df34a1973ba753e7241ce3a08ef979ddd7bea5 /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml README.md ./
COPY src ./src

# Build the package
RUN uv build --wheel

# Runtime stage
FROM python:3.14-slim@sha256:fb83750094b46fd6b8adaa80f66e2302ecbe45d513f6cece637a841e1025b4ca

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

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Switch to non-root user
USER lazyecs

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]