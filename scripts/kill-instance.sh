#!/bin/bash

# Script to kill a specific KohTravel2 development instance
# Usage: ./scripts/kill-instance.sh [offset]

OFFSET=${1:-0}

# Calculate ports
FRONTEND_PORT=$((3000 + OFFSET))
API_PORT=$((8000 + OFFSET))
AGENT_PORT=$((8001 + OFFSET))

echo "🛑 Killing KohTravel2 Development Instance (Offset: $OFFSET)"
echo "   Ports: $FRONTEND_PORT, $API_PORT, $AGENT_PORT"

# Kill processes on these ports
for port in $FRONTEND_PORT $API_PORT $AGENT_PORT; do
    if lsof -ti:$port > /dev/null 2>&1; then
        echo "   Killing process on port $port..."
        lsof -ti:$port | xargs kill -9
    else
        echo "   No process found on port $port"
    fi
done

echo "✅ Instance stopped"