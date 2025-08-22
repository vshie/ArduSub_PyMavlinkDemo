#!/bin/bash

# Build script for ArduSub PyMavlink Control Extension

set -e

echo "🚢 Building ArduSub PyMavlink Control Extension..."

# Set variables
IMAGE_NAME="ardusub-pymavlink-control"
VERSION="0.0.1"
DOCKER_USERNAME=${DOCKER_USERNAME:-"your-username"}

echo "📦 Building Docker image: $IMAGE_NAME:$VERSION"

# Build the Docker image
docker build -t $IMAGE_NAME:$VERSION .

if [ $? -eq 0 ]; then
    echo "✅ Docker image built successfully!"
    
    # Tag for Docker Hub
    echo "🏷️  Tagging image for Docker Hub..."
    docker tag $IMAGE_NAME:$VERSION $DOCKER_USERNAME/$IMAGE_NAME:$VERSION
    docker tag $IMAGE_NAME:$VERSION $DOCKER_USERNAME/$IMAGE_NAME:latest
    
    echo "📋 Image tags created:"
    echo "   - $IMAGE_NAME:$VERSION"
    echo "   - $DOCKER_USERNAME/$IMAGE_NAME:$VERSION"
    echo "   - $DOCKER_USERNAME/$IMAGE_NAME:latest"
    
    echo ""
    echo "🚀 To deploy to Docker Hub, run:"
    echo "   docker push $DOCKER_USERNAME/$IMAGE_NAME:$VERSION"
    echo "   docker push $DOCKER_USERNAME/$IMAGE_NAME:latest"
    
    echo ""
    echo "🔧 To test locally, run:"
    echo "   docker run -p 8000:8000 $IMAGE_NAME:$VERSION"
    echo ""
    echo "   Or use docker-compose:"
    echo "   docker-compose up"
    
else
    echo "❌ Docker build failed!"
    exit 1
fi
