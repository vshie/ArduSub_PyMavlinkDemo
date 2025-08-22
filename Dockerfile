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
    "Binds":["/usr/blueos/extensions/ardusub-pymavlink-control:/app"],\
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

# Copy application files explicitly to ensure they're in the right place
COPY app/main.py .
COPY app/static/ ./static/

# Copy requirements and install Python dependencies
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create logs directory
RUN mkdir -p /app/logs

# Expose port (matching videorecorder)
EXPOSE 8000

# Set environment variables
ENV FLASK_APP=main.py
ENV FLASK_ENV=production
ENV FLASK_RUN_PORT=8000

# Simple CMD to run the application
CMD ["python", "main.py"]
