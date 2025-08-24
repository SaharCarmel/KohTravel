from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os

app = FastAPI(
    title="KohTravel API",
    description="Travel planning and management API",
    version="1.0.0"
)

# Auto-solve CORS as requested - supports multiple development instances
import re

def cors_origin_validator(origin: str) -> bool:
    """Allow localhost ports 3000-3100 and 8000-8100 for multiple dev instances"""
    if not origin:
        return False
    
    # Allow Vercel deployments
    if ".vercel.app" in origin or "kohtravel.vercel.app" in origin:
        return True
    
    # Allow localhost with ports in development ranges
    localhost_pattern = r"^https?://localhost:(?P<port>\d+)$"
    match = re.match(localhost_pattern, origin)
    
    if match:
        port = int(match.group("port"))
        # Allow frontend ports (3000-3100) and backend ports (8000-8100)
        return (3000 <= port <= 3100) or (8000 <= port <= 8100)
    
    return False

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://localhost:[3-8][0-9]{3}$|.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "KohTravel API is running", "status": "healthy"}

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "KohTravel API"}

@app.get("/api/travels")
def get_travels():
    # Placeholder endpoint for travel data
    return {"travels": [], "message": "Travel data endpoint ready"}

@app.get("/api/destinations")
def get_destinations():
    # Placeholder endpoint for destinations
    return {"destinations": [], "message": "Destinations endpoint ready"}

# For Vercel serverless function compatibility
def handler(request):
    return app(request)