# Kisan Saathi — Production Dockerfile
FROM python:3.12-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy dependency manifest first (cache layer)
COPY requirements.txt .
RUN uv pip install -r requirements.txt --system

# Copy application code
COPY . .

# Expose MCP server port
EXPOSE 8000

# Default entrypoint: run the FastMCP server
CMD ["uv", "run", "python", "mcp/kisan_mcp_server.py"]
