#!/bin/bash
# Quick start script for openScience Docker environment

set -e

echo "🚀 openScience Docker Quick Start"
echo "=================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✓ Docker is installed"
echo "✓ Docker Compose is installed"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and update the configuration"
    echo "   Especially: DB_PASSWORD, REDIS_PASSWORD, and SECRET_KEY"
    echo ""
    read -p "Press Enter to continue or Ctrl+C to exit and edit .env first..."
fi

# Build images
echo ""
echo "🔨 Building Docker images..."
docker-compose build

echo ""
echo "✓ Images built successfully"
echo ""

# Start services
echo "🚀 Starting services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service health
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "=================================="
echo "✅ openScience is now running!"
echo ""
echo "Access the following services:"
echo "  🌐 Web UI:    http://localhost:3000"
echo "  🔌 API:       http://localhost:5000"
echo "  ❤️  Health:    http://localhost:5000/health"
echo "  🌸 Flower:    http://localhost:5555"
echo ""
echo "Useful commands:"
echo "  📋 View logs:       docker-compose logs -f"
echo "  🛑 Stop services:   docker-compose down"
echo "  🔄 Restart:         docker-compose restart"
echo "  🧹 Clean up:        docker-compose down -v"
echo ""
echo "For more information, see docker/README.md"
