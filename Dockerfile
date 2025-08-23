FROM python:3.11-slim

# BlueOS Extension metadata labels
LABEL version="0.0.1"
LABEL type="extension"
LABEL requirements="core >= 1.1"

WORKDIR /app

# Copy requirements and install Python dependencies first
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY app/ .

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create logs directory
RUN mkdir -p /app/logs

# Expose port
EXPOSE 8000

# Set environment variables
ENV FLASK_APP=main.py
ENV FLASK_ENV=production
ENV FLASK_RUN_PORT=8000

# BlueOS permissions label
LABEL permissions='\
{\
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
  },\
  "ExposedPorts": {\
    "8000/tcp": {}\
  }\
}'

# Start command
CMD ["python", "main.py"]
