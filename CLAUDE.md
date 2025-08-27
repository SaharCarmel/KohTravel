# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

KohTravel is a 3-service architecture for AI-powered travel document management:

### Core Services
- **Frontend** (port 3000): Next.js + TypeScript + Tailwind CSS chat interface 
- **KohTravel API** (port 8000): FastAPI backend with document processing and agent integration
- **Agent Infrastructure** (port 8001): General-purpose AI agent service for tool execution

### Critical Separation
**Agent Infrastructure is general-purpose software** - no KohTravel-specific code should be written there. All KohTravel logic stays in the KohTravel API service layer.

## Development Commands

```bash
# Start all services
npm run dev

# Individual services  
npm run dev:frontend  # Frontend only
npm run dev:api      # KohTravel API only  
npm run dev:agent    # Agent infrastructure only

# Database operations
npm run dev:migrate  # Run database migrations

# Cleanup
npm run kill-ports   # Kill stuck processes on dev ports
```

## Key Architecture Patterns

### Agent System Flow
1. Frontend calls KohTravel API (port 8000) 
2. KohTravel API loads custom prompts from `prompts/` directory
3. KohTravel API calls Agent Infrastructure (port 8001) with custom prompt
4. Agent Infrastructure executes tools and returns results

### Document Processing Pipeline
1. User uploads PDF → `api/routes/documents.py`
2. Background processing → `api/services/document_processor.py` with Docling + Claude
3. Auto-classification with existing categories or new category creation
4. Structured data extraction and storage

### AI Agent Tool System
- **Tools defined in**: `api/routes/agent_tools.py` (KohTravel-specific)
- **Tool prompts in**: `prompts/tools/` (workflow guidance)
- **Agent prompt in**: `prompts/agents/travel-assistant.md` (main behavior)
- **External tool loading**: Agent infrastructure discovers tools via `/available_tools` endpoint

## Database Environment

### Development
- PostgreSQL via Railway (connection string in `.env.development`)
- Auto-migrations on startup
- User migration service handles auth integration

### Migrations
```bash
cd api
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```

## Document Classification System

The AI classification system:
1. Sees existing document categories before deciding
2. Creates new categories intelligently ("Legal Policy", "Activity Voucher")  
3. Eliminates hardcoded document type assumptions
4. Scales automatically to any document type

## Agent Workflow (Generalized)

**Mandatory 4-step sequence for all queries:**
1. `get_document_categories()` - discover available document types
2. `search_documents(category="relevant")` - search by discovered categories  
3. `get_document(document_id="doc_X")` - get complete raw text
4. Extract specific information from full document content

This approach works for any document type without code changes.

## Technology Stack

### Backend Dependencies (uv managed)
- **FastAPI**: Web framework with async support
- **SQLAlchemy**: ORM with Alembic migrations  
- **Anthropic**: Claude API integration
- **Docling**: PDF text extraction
- **structlog**: Production logging

### Frontend Dependencies (npm managed)  
- **Next.js 15**: React framework with SSR
- **NextAuth**: Authentication with Google/GitHub
- **Tailwind CSS**: Utility-first styling
- **shadcn/ui**: Component library

### Agent Infrastructure Dependencies (uv managed)
- **FastAPI**: General-purpose agent API
- **Anthropic**: Claude integration with tool calling
- **structlog**: Structured logging with rotation

## Development Notes

- Use `uv` for Python package management (never pip)
- Agent infrastructure must remain general-purpose
- All KohTravel logic stays in KohTravel API service
- Document processing is async with status tracking
- Frontend routes through KohTravel API, not directly to agent infrastructure