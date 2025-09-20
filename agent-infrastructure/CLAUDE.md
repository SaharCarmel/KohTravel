# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

The Agent Infrastructure is a standalone, reusable AI agent platform designed to be integrated into applications as a backend service. It operates as an "Agent OS" - managing agent lifecycle, sessions, tools, and conversations.

### Core Components

- **Agent Management** - Agent definitions, system prompts, and tool configurations
- **Session Management** - User conversations and context persistence
- **Tool System** - Internal tools and external tool integration
- **Provider System** - AI model providers (Anthropic Claude, future OpenAI support)
- **Database Layer** - PostgreSQL for agent data, sessions, and user context

### Key Architecture Patterns

**Agent-as-a-Service Model**
- Apps (like KohTravel) integrate via HTTP API
- One agent definition per app, personalized execution per user
- External tools provided by integrating applications
- All agent data managed by the infrastructure

**Multi-Tenant Session Management**
- Each user gets personalized sessions with shared agent
- User-specific context and custom prompts stored separately
- Authentication passed per request (no credential storage)

## Development Commands

```bash
# Start development server
../scripts/dev-agent.sh

# Manual start (from agent-infrastructure directory)
uv run python -m src.server.main --reload --port 8001

# Install dependencies
uv sync --dev

# Run tests
../scripts/test-agent.py

# Specific tests
../scripts/test-agent.py --test health
../scripts/test-agent.py --test chat
```

## Environment Configuration

Required environment variables:

```bash
# Core configuration
ANTHROPIC_API_KEY=sk-your-key-here
AGENT_OS_DB_URL=postgresql://user:pass@localhost:5432/agent_os_db

# Optional configuration
PORT=8001
CORS_ORIGINS=*
AUTH_ENABLED=false
LOG_LEVEL=INFO
```

## Database Architecture

The infrastructure maintains its own PostgreSQL database separate from integrating applications:

### Core Tables
- `agents` - Agent definitions (prompts, tools, configuration)
- `user_agent_context` - User-specific customizations and preferences
- `sessions` - Conversation sessions per user per agent
- Database migrations via Alembic

### Database Operations
```bash
# Run migrations
cd agent-infrastructure
uv run alembic upgrade head

# Create new migration
uv run alembic revision --autogenerate -m "description"
```

## API Structure

### Agent Management
- `POST /api/agents` - Create new agent
- `GET /api/agents/{agent_id}` - Get agent configuration
- `PUT /api/agents/{agent_id}/prompt` - Update system prompt
- `PUT /api/agents/{agent_id}/tools` - Configure tools

### Session & Chat
- `POST /api/agents/{agent_id}/users/{user_id}/sessions` - Create session
- `POST /api/agents/{agent_id}/sessions/{session_id}/chat` - Send message
- `GET /api/agents/{agent_id}/sessions/{session_id}/history` - Get conversation

### Health & Monitoring
- `GET /health/` - Service health check
- `GET /health/ready` - Readiness probe
- `GET /health/live` - Liveness probe

## Tool Integration

### Internal Tools
Built-in tools available to all agents:
- File operations (read/write with path restrictions)
- Database queries (configured table access)
- Document search capabilities

### External Tools
Applications register tool endpoints that agents can call:
```python
# Tool registration example
{
    "name": "search_documents",
    "endpoint": "https://app.com/api/agent/tools/search_documents",
    "description": "Search user documents",
    "input_schema": {...},
    "output_schema": {...}
}
```

## Integration Patterns

### App Integration Flow
1. App creates agent definition via API
2. App handles user authentication
3. App passes user auth context with each chat request
4. Agent Infrastructure forwards auth to external tools
5. Agent returns personalized responses

### Authentication Pattern
User authentication is passed per request, never stored:
```python
POST /api/agents/{agent_id}/sessions/{session_id}/chat
{
    "message": "Find my documents",
    "user_auth": {
        "token": "user_jwt_token",
        "user_id": "user123"
    }
}
```

## Key Design Principles

- **Stateless Authentication** - No credential storage, pass auth per request
- **Database Separation** - Infrastructure maintains its own database
- **Tool Agnosticism** - Support any HTTP-accessible tool endpoint
- **Session Persistence** - Conversations stored indefinitely
- **User Personalization** - Shared agent definition, personalized execution

## Future Architecture

The infrastructure is designed to evolve toward:
- Tool marketplace with sandboxing
- Multi-agent orchestration
- Advanced monitoring and observability
- Plugin architecture for extensibility