#!/bin/bash

# Skill-Stake Learning Platform Development Setup Script

set -e

echo "🚀 Setting up Skill-Stake Learning Platform development environment..."

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

# Copy environment files if they don't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your API keys and configuration"
fi

if [ ! -f frontend/.env.local ]; then
    echo "📝 Creating frontend/.env.local file from template..."
    cp frontend/.env.local.example frontend/.env.local
    echo "⚠️  Please edit frontend/.env.local with your API keys"
fi

# Build and start services
echo "🏗️  Building Docker images..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 10

# Run database migrations
echo "🗄️  Running database migrations..."
docker-compose exec -T backend alembic upgrade head

echo "✅ Development environment setup complete!"
echo ""
echo "🌐 Services are now running:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:8000"
echo "   API Documentation: http://localhost:8000/docs"
echo ""
echo "📋 Next steps:"
echo "   1. Edit .env and frontend/.env.local with your API keys"
echo "   2. Visit http://localhost:3000 to see the application"
echo "   3. Check logs with: docker-compose logs -f"
echo ""
echo "🛑 To stop services: docker-compose down"