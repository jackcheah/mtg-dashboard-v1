#!/bin/bash

# MTG Tournament Dashboard - Docker Build and Run Script

echo "🐳 MTG Tournament Dashboard - Docker Deployment"
echo "================================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if required files exist
if [ ! -f "tournament_dashboard.py" ]; then
    echo "❌ tournament_dashboard.py not found in current directory"
    exit 1
fi

if [ ! -f "templates/dashboard.html" ]; then
    echo "❌ templates/dashboard.html not found"
    exit 1
fi

if [ ! -f "July_CEDH_Event/13th July CEDH Participant List.xlsx" ]; then
    echo "❌ Excel participant file not found"
    exit 1
fi

echo "✅ All required files found"

# Stop any existing container
echo "🛑 Stopping existing containers..."
docker-compose down

# Build and start the container
echo "🏗️  Building and starting container..."
docker-compose up -d --build

# Wait for container to be ready
echo "⏳ Waiting for container to be ready..."
sleep 5

# Check if container is running
if docker ps | grep -q "mtg-tournament-dashboard"; then
    echo "✅ Container is running successfully!"
    echo ""
    echo "🎯 Access the application at:"
    echo "   Local: http://localhost:5000"
    echo "   Network: http://$(hostname -I | awk '{print $1}'):5000"
    echo ""
    echo "📊 Container status:"
    docker ps --filter "name=mtg-tournament-dashboard"
    echo ""
    echo "📝 To view logs: docker-compose logs -f"
    echo "🛑 To stop: docker-compose down"
else
    echo "❌ Container failed to start. Check logs:"
    docker-compose logs
    exit 1
fi 