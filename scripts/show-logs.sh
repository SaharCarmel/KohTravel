#!/bin/bash

# Show logs for a specific instance
# Usage: ./scripts/show-logs.sh [offset] [service]
# service can be: frontend, api, agent, all

OFFSET=${1:-0}
SERVICE=${2:-all}

show_service_logs() {
    local service=$1
    local color=$2
    
    echo -e "\n${color}=== $service LOGS (Offset: $OFFSET) ===${NC}"
    
    if [ -f "logs/$service-$OFFSET.log" ]; then
        tail -n 20 "logs/$service-$OFFSET.log" | sed "s/^/${color}[$service]${NC} /"
    else
        echo "❌ No logs found for $service-$OFFSET"
    fi
}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m' 
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "📋 KohTravel2 Instance Logs (Offset: $OFFSET)"

case $SERVICE in
    frontend|f)
        show_service_logs "frontend" "$BLUE"
        ;;
    api|a)
        show_service_logs "api" "$GREEN"
        ;;
    agent|ag)
        show_service_logs "agent" "$YELLOW"
        ;;
    all|*)
        show_service_logs "frontend" "$BLUE"
        show_service_logs "api" "$GREEN" 
        show_service_logs "agent" "$YELLOW"
        ;;
esac

echo -e "\n💡 For live logs: tail -f logs/{frontend,api,agent}-$OFFSET.log"