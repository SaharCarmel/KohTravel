#!/usr/bin/env python3
"""
Test database connection and verify tables were created
"""
from database import engine, SessionLocal
from sqlalchemy import text

def test_connection():
    print("🧪 Testing database connection...")
    
    try:
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Connected to PostgreSQL: {version[:50]}...")
        
        # Test session
        db = SessionLocal()
        
        # Check if tables exist
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            
            tables = [row[0] for row in result.fetchall()]
            print(f"\n📋 Tables created: {len(tables)}")
            for table in tables:
                print(f"  - {table}")
        
        # Check migration history
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.fetchone()
            if version:
                print(f"\n🔄 Migration version: {version[0]}")
            else:
                print("\n❌ No migration version found")
        
        db.close()
        print("\n✅ Database setup successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Database error: {e}")
        return False

if __name__ == "__main__":
    test_connection()