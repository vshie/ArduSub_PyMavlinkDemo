FROM python:3.11-slim

# BlueOS Extension metadata labels
LABEL version="0.0.1"
LABEL type="extension"
LABEL permissions='\
{\
  "ExposedPorts": {\
    "8000/tcp": {}\
  },\
  "HostConfig": {\
    "Binds":["/usr/blueos/extensions/ardusub-pymavlink-control:/app/logs"],\
    "ExtraHosts": ["host.docker.internal:host-gateway"],\
    "PortBindings": {\
      "8000/tcp": [\
        {\
          "HostPort": ""\
        }\
      ]\
    }\
  }\
}'
LABEL requirements="core >= 1.1"

WORKDIR /app

# Install system dependencies (matching videorecorder)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files explicitly to ensure they're in the right place
COPY app/main.py .
COPY app/static/ ./static/

# Debug: Show what's actually in the container
RUN echo "=== Container contents after copying ===" && \
    pwd && \
    echo "--- Root directory ---" && \
    ls -la && \
    echo "--- Static directory ---" && \
    ls -la static/ && \
    echo "--- main.py details ---" && \
    ls -la main.py

# Create logs directory
RUN mkdir -p /app/logs

# Expose port (matching videorecorder)
EXPOSE 8000

# Set environment variables
ENV FLASK_APP=main.py
ENV FLASK_ENV=production
ENV FLASK_RUN_PORT=8000

# Debug startup command to see what's in the container at runtime
CMD ["sh", "-c", "echo '=== Runtime Debug ===' && pwd && ls -la && echo '=== BlueOS mount point ===' && ls -la /blueos/ && echo '=== Starting main.py ===' && python main.py"]
