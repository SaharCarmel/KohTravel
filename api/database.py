from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load development environment by default
env_file = os.getenv("ENV_FILE", "../.env.development")
load_dotenv(env_file)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

# Configure SSL for Railway PostgreSQL - disable SSL verification for development
engine_kwargs = {}
if "railway" in DATABASE_URL.lower() or "rlwy.net" in DATABASE_URL.lower():
    engine_kwargs["connect_args"] = {
        "sslmode": "disable"
    }

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()