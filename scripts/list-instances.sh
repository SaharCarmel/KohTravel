#!/bin/bash

# Script to list running KohTravel2 development instances
# Usage: ./scripts/list-instances.sh

echo "🔍 KohTravel2 Development Instances"
echo "=================================="

found_any=false

# Check common port offsets
for offset in 0 10 20 30; do
    FRONTEND_PORT=$((3000 + offset))
    API_PORT=$((8000 + offset))
    AGENT_PORT=$((8001 + offset))
    
    # Check if any port in this offset range is in use
    active_ports=()
    
    if lsof -ti:$FRONTEND_PORT > /dev/null 2>&1; then
        active_ports+=("Frontend:$FRONTEND_PORT")
    fi
    
    if lsof -ti:$API_PORT > /dev/null 2>&1; then
        active_ports+=("API:$API_PORT")
    fi
    
    if lsof -ti:$AGENT_PORT > /dev/null 2>&1; then
        active_ports+=("Agent:$AGENT_PORT")
    fi
    
    # If any ports are active, show this instance
    if [ ${#active_ports[@]} -gt 0 ]; then
        found_any=true
        echo ""
        echo "📱 Instance (Offset: $offset)"
        echo "   🌐 Frontend: http://localhost:$FRONTEND_PORT $(lsof -ti:$FRONTEND_PORT > /dev/null 2>&1 && echo '✅' || echo '❌')"
        echo "   🔌 API:      http://localhost:$API_PORT $(lsof -ti:$API_PORT > /dev/null 2>&1 && echo '✅' || echo '❌')"
        echo "   🤖 Agent:    http://localhost:$AGENT_PORT $(lsof -ti:$AGENT_PORT > /dev/null 2>&1 && echo '✅' || echo '❌')"
        echo "   ⚡ Kill:     ./scripts/kill-instance.sh $offset"
    fi
done

if [ "$found_any" = false ]; then
    echo ""
    echo "No active instances found."
    echo ""
    echo "💡 Start an instance:"
    echo "   ./scripts/dev-instance.sh 0   # Default ports"
    echo "   ./scripts/dev-instance.sh 10  # Offset +10"
    echo "   ./scripts/dev-instance.sh 20  # Offset +20"
fi

echo ""