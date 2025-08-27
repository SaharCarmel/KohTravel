#!/bin/bash

# Development script for running KohTravel2 with configurable port offsets
# Usage: ./scripts/dev-instance.sh [offset]
# Example: ./scripts/dev-instance.sh 10  # Runs on ports 3010, 8010, 8011

set -e

# Get port offset from argument or default to 0
OFFSET=${1:-0}

# Calculate ports
FRONTEND_PORT=$((3000 + OFFSET))
API_PORT=$((8000 + OFFSET))
AGENT_PORT=$((8001 + OFFSET))

echo "🚀 Starting KohTravel2 Development Instance"
echo "   📊 Port Offset: $OFFSET"
echo "   🌐 Frontend: http://localhost:$FRONTEND_PORT"
echo "   🔌 API: http://localhost:$API_PORT"
echo "   🤖 Agent: http://localhost:$AGENT_PORT"
echo ""

# Check if ports are available
check_port() {
    local port=$1
    if lsof -ti:$port > /dev/null 2>&1; then
        echo "❌ Port $port is already in use!"
        echo "   Kill existing process: lsof -ti:$port | xargs kill -9"
        return 1
    fi
}

echo "🔍 Checking port availability..."
if ! check_port $FRONTEND_PORT || ! check_port $API_PORT || ! check_port $AGENT_PORT; then
    echo ""
    echo "💡 Tip: Try a different offset: ./scripts/dev-instance.sh $((OFFSET + 10))"
    exit 1
fi

# Set environment variables for this instance
export SERVICE_PORT_OFFSET=$OFFSET
export PORT=$FRONTEND_PORT
export FRONTEND_PORT=$FRONTEND_PORT
export API_PORT=$API_PORT
export AGENT_PORT=$AGENT_PORT

# Ensure we have fallbacks if variables aren't set
export FRONTEND_PORT=${FRONTEND_PORT:-$((3000 + OFFSET))}
export API_PORT=${API_PORT:-$((8000 + OFFSET))}
export AGENT_PORT=${AGENT_PORT:-$((8001 + OFFSET))}

# URLs for service discovery
export NEXT_PUBLIC_AGENT_URL="http://localhost:$AGENT_PORT"
export AGENT_INFRASTRUCTURE_URL="http://localhost:$AGENT_PORT"
export MAIN_API_URL="http://localhost:$API_PORT"

# Update the agent development script environment
export CORS_ORIGINS="http://localhost:$FRONTEND_PORT,http://localhost:$API_PORT"

echo "✅ Ports available. Starting services..."
echo ""

# Start all services in parallel using the existing dev command
npm run dev