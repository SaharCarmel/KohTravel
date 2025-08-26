# Agent Infrastructure

Standalone agent infrastructure for multi-project AI agent management. This service provides a reusable, configurable foundation for building AI agents that can be integrated into different projects.

## 🏗️ Architecture

```
Agent Infrastructure (Port 8001)
├── Core Agent Framework
│   ├── Conversation Management
│   ├── Streaming Responses
│   └── Context Injection
├── Provider System
│   ├── Anthropic Claude
│   └── OpenAI (future)
├── Tool System
│   ├── Database Query
│   ├── Document Search
│   └── File Operations
└── FastAPI Server
    ├── REST API
    ├── Server-Sent Events
    └── Authentication
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your configuration
nano .env

# Required: Add your Anthropic API key
ANTHROPIC_API_KEY=sk-your-key-here
```

### 2. Install Dependencies

```bash
# Using uv (recommended)
uv sync --dev

# Or using pip
pip install -e .
```

### 3. Start the Server

```bash
# Development server
../scripts/dev-agent.sh

# Or manually
uv run python -m src.server.main --reload --port 8001
```

### 4. Test the Service

```bash
# Run all tests
../scripts/test-agent.py

# Or specific tests
../scripts/test-agent.py --test health
../scripts/test-agent.py --test chat
```

## 📡 API Endpoints

### Health
- `GET /health/` - Service health check
- `GET /health/ready` - Readiness probe
- `GET /health/live` - Liveness probe

### Agent
- `POST /agent/chat` - Send message (complete response)
- `POST /agent/chat/stream` - Send message (streaming response)
- `GET /agent/conversation/{session_id}` - Get conversation history
- `DELETE /agent/conversation/{session_id}` - Clear conversation
- `GET /agent/agents` - List active agents
- `GET /agent/tools` - List available tools

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | Required |
| `DATABASE_URL` | PostgreSQL connection string | Optional |
| `PORT` | Server port | 8001 |
| `CORS_ORIGINS` | Allowed CORS origins | * |
| `AUTH_ENABLED` | Enable authentication | false |
| `LOG_LEVEL` | Logging level | INFO |

### Project Configuration

Create YAML configs in `/configs/` for project-specific settings:

```yaml
# configs/myproject.yaml
project:
  name: "MyProject"
  
agent:
  system_prompt: "You are a helpful assistant for MyProject..."
  
provider:
  model: "claude-3-5-sonnet-20241022"
  temperature: 0.1
  
tools:
  enabled:
    - "database_query"
    - "search_documents"
```

## 🛠️ Available Tools

### Database Query Tool
- Execute safe read-only SQL queries
- Configurable table access
- Automatic result limiting

### Document Search Tool  
- Search user documents by content
- Category filtering
- Relevance scoring

### File Operations Tools
- Read files (with path restrictions)
- Write files (optional, configurable)
- List directories

## 🔌 Integration

### Python Client

```python
from integrations.kohtravel.src.services.agent_client import AgentClient

async with AgentClient("http://localhost:8001") as client:
    response = await client.send_message(
        session_id="user-session-123",
        message="Hello, how can you help?",
        user_id="user-456",
        project="myproject"
    )
    print(response["message"])
```

### Streaming Client

```python
async with AgentClient("http://localhost:8001") as client:
    async for chunk in client.stream_message(
        session_id="user-session-123",
        message="Tell me about my documents",
        user_id="user-456",
        project="myproject"
    ):
        if chunk["type"] == "content":
            print(chunk["data"]["content"], end="")
```

### FastAPI Integration

```python
from fastapi import FastAPI
from integrations.kohtravel.src.services.agent_client import AgentClient

app = FastAPI()

@app.post("/chat")
async def chat(message: str, user_id: str):
    async with AgentClient() as client:
        return await client.send_message(
            session_id=f"web-{user_id}",
            message=message,
            user_id=user_id
        )
```

## 🏃‍♂️ Development

### Running Tests

```bash
# All tests
./scripts/test-agent.py

# Specific tests  
./scripts/test-agent.py --test health
./scripts/test-agent.py --test stream
```

### Development Server

```bash
# Auto-reload on changes
./scripts/dev-agent.sh

# Manual start
cd agent-infrastructure
uv run python -m src.server.main --reload
```

### Adding New Tools

```python
from src.tools.base import Tool, ToolResult

class MyCustomTool(Tool):
    def __init__(self):
        super().__init__("my_tool", "Description of my tool")
        self.add_parameter("param1", "string", "Parameter description")
    
    async def execute(self, parameters, context):
        # Tool implementation
        return ToolResult(
            success=True,
            content="Tool result",
            metadata={"param1": parameters["param1"]}
        )
```

## 🔐 Security

- **Input validation** on all parameters
- **SQL injection prevention** with parameterized queries  
- **File access restrictions** with configurable allowed paths
- **Authentication middleware** (optional)
- **User isolation** for database queries

## 🚢 Deployment

### Docker (Recommended)

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install uv
RUN uv sync --frozen

EXPOSE 8001
CMD ["uv", "run", "python", "-m", "src.server.main"]
```

### Vercel/Railway

The service is designed to work with serverless platforms:

```json
{
  "builds": [
    {
      "src": "agent-infrastructure/src/server/main.py",
      "use": "@vercel/python"
    }
  ]
}
```

## 🎯 Future Roadmap

- [ ] OpenAI provider support
- [ ] WebSocket connections  
- [ ] Vector database integration
- [ ] Multi-agent orchestration
- [ ] Plugin marketplace
- [ ] Monitoring dashboard

## 📄 License

MIT License - see LICENSE file for details.