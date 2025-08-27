#!/bin/bash

# Enhanced development script with comprehensive logging
# Usage: ./scripts/dev-instance-with-logs.sh [offset]

set -e

OFFSET=${1:-0}
FRONTEND_PORT=$((3000 + OFFSET))
API_PORT=$((8000 + OFFSET))
AGENT_PORT=$((8001 + OFFSET))

echo "🚀 Starting KohTravel2 Development Instance with Enhanced Logging"
echo "   📊 Port Offset: $OFFSET"
echo "   🌐 Frontend: http://localhost:$FRONTEND_PORT"
echo "   🔌 API: http://localhost:$API_PORT"
echo "   🤖 Agent: http://localhost:$AGENT_PORT"
echo ""

# Check port availability
check_port() {
    local port=$1
    if lsof -ti:$port > /dev/null 2>&1; then
        echo "❌ Port $port is already in use!"
        return 1
    fi
}

echo "🔍 Checking port availability..."
if ! check_port $FRONTEND_PORT || ! check_port $API_PORT || ! check_port $AGENT_PORT; then
    echo "💡 Kill existing: ./scripts/kill-instance.sh $OFFSET"
    exit 1
fi

# Set environment variables
export SERVICE_PORT_OFFSET=$OFFSET
export FRONTEND_PORT=$FRONTEND_PORT
export API_PORT=$API_PORT
export AGENT_PORT=$AGENT_PORT

# Service URLs
export NEXT_PUBLIC_AGENT_URL="http://localhost:$AGENT_PORT"
export AGENT_INFRASTRUCTURE_URL="http://localhost:$AGENT_PORT"
export MAIN_API_URL="http://localhost:$API_PORT"
export CORS_ORIGINS="http://localhost:$FRONTEND_PORT,http://localhost:$API_PORT"

# Create logs directory
mkdir -p logs

echo "✅ Starting services with individual log files..."
echo "📋 Logs will be saved to:"
echo "   🌐 Frontend: logs/frontend-$OFFSET.log"
echo "   🔌 API:      logs/api-$OFFSET.log" 
echo "   🤖 Agent:    logs/agent-$OFFSET.log"
echo ""

# Start Frontend
echo "🌐 Starting Frontend on port $FRONTEND_PORT..."
cd frontend && PORT=$FRONTEND_PORT npm run dev > "../logs/frontend-$OFFSET.log" 2>&1 &
FRONTEND_PID=$!
cd ..

# Start API
echo "🔌 Starting API on port $API_PORT..."
cd api && PORT=$API_PORT uv run --with fastapi --with uvicorn --with python-multipart --with psycopg2-binary --with python-dotenv uvicorn main:app --reload --host 0.0.0.0 --port $API_PORT > "../logs/api-$OFFSET.log" 2>&1 &
API_PID=$!
cd ..

# Start Agent Infrastructure
echo "🤖 Starting Agent Infrastructure on port $AGENT_PORT..."
./scripts/dev-agent.sh > "logs/agent-$OFFSET.log" 2>&1 &
AGENT_PID=$!

# Save PIDs for cleanup
echo "$FRONTEND_PID" > "logs/frontend-$OFFSET.pid"
echo "$API_PID" > "logs/api-$OFFSET.pid"
echo "$AGENT_PID" > "logs/agent-$OFFSET.pid"

echo ""
echo "🎉 All services started! Monitoring logs..."
echo "🔍 Use these commands to monitor:"
echo "   tail -f logs/frontend-$OFFSET.log"
echo "   tail -f logs/api-$OFFSET.log"
echo "   tail -f logs/agent-$OFFSET.log"
echo ""
echo "🛑 To stop: ./scripts/kill-instance.sh $OFFSET"
echo ""

# Monitor all logs in parallel
echo "📊 Live Logs (Ctrl+C to stop monitoring, services keep running):"
echo "==============================================================="
echo ""

# Use multitail if available, otherwise use tail
if command -v multitail >/dev/null 2>&1; then
    multitail \
        -i "logs/frontend-$OFFSET.log" \
        -i "logs/api-$OFFSET.log" \
        -i "logs/agent-$OFFSET.log"
else
    # Fallback to tail with color coding
    tail -f "logs/frontend-$OFFSET.log" "logs/api-$OFFSET.log" "logs/agent-$OFFSET.log" | \
    while IFS= read -r line; do
        case "$line" in
            *frontend*) echo -e "\033[34m[FRONTEND]\033[0m $line" ;;
            *api*) echo -e "\033[32m[API]\033[0m $line" ;;
            *agent*) echo -e "\033[33m[AGENT]\033[0m $line" ;;
            *) echo "$line" ;;
        esac
    done
fi