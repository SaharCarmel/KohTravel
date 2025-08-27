"""
Agent health check endpoint as Vercel serverless function
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from shared.config import get_cors_origins

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def health_check():
    """Agent service health check"""
    return {
        "status": "healthy",
        "service": "agent-infrastructure",
        "version": "0.1.0",
        "environment": os.getenv('VERCEL_ENV', 'development')
    }


# Export for Vercel
def handler(request, context):
    """Vercel serverless function handler"""
    return app