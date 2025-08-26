#!/bin/bash

# Development script for running the agent infrastructure

set -e

echo "🚀 Starting Agent Infrastructure Development Server"

# Check if we're in the right directory
if [ ! -f "agent-infrastructure/pyproject.toml" ]; then
    echo "❌ Please run this script from the KohTravel project root"
    exit 1
fi

# Navigate to agent infrastructure directory from project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$( dirname "$SCRIPT_DIR" )"
cd "$PROJECT_ROOT/agent-infrastructure"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "📋 Creating .env from example..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your actual configuration"
fi

# Install dependencies with uv
echo "📦 Installing dependencies with uv..."
uv sync --dev

# Set environment variables for development
export DEBUG=true
export ENVIRONMENT=development
export AUTH_ENABLED=false
export CORS_ORIGINS="http://localhost:3000,http://localhost:8000"

# Load environment variables from .env if they exist
if [ -f ".env" ]; then
    echo "🔧 Loading environment variables from .env"
    export $(grep -v '^#' .env | xargs)
fi

# Check required environment variables
if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "sk-your-anthropic-key-here" ]; then
    echo "❌ ANTHROPIC_API_KEY is required. Please set it in .env file"
    exit 1
fi

# Run the server
echo "🌐 Starting agent server on http://localhost:8001"
echo "📚 API documentation: http://localhost:8001/docs"
echo "🔍 Health check: http://localhost:8001/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start with verbose output to see any errors  
export PYTHONPATH=.
exec uv run uvicorn src.server.main:create_app --factory --reload --host 0.0.0.0 --port 8001