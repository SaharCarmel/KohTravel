"""
Seed script for calendar events.
Run with: uv run python seed_calendar_events.py
"""

import asyncio
from datetime import datetime, timedelta
from database import get_db
from models.calendar_event import CalendarEvent
from models.user import User
from sqlalchemy.orm import Session

# Mock calendar events data - Thailand Adventure Trip
MOCK_EVENTS = [
    {
        "title": "Flight to Bangkok",
        "description": "Emirates flight EK 123 - Departure from JFK",
        "location": "Don Mueang Airport (DMK)",
        "start_datetime": datetime(2025, 8, 30, 8, 30),
        "end_datetime": datetime(2025, 8, 30, 23, 45),
        "event_type": "flight",
        "color": "bg-blue-500"
    },
    {
        "title": "Hotel Check-in",
        "description": "Chatrium Hotel Riverside Bangkok - Room 1205",
        "location": "Chatrium Hotel Riverside Bangkok",
        "start_datetime": datetime(2025, 8, 30, 15, 0),
        "end_datetime": datetime(2025, 8, 30, 16, 0),
        "event_type": "accommodation",
        "color": "bg-green-500"
    },
    {
        "title": "Temple Tour",
        "description": "Guided tour of Wat Pho & Grand Palace",
        "location": "Grand Palace, Bangkok",
        "start_datetime": datetime(2025, 8, 31, 9, 0),
        "end_datetime": datetime(2025, 8, 31, 16, 0),
        "event_type": "activity",
        "color": "bg-purple-500"
    },
    {
        "title": "Cooking Class",
        "description": "Learn to cook authentic Thai dishes",
        "location": "Thai Cooking Academy, Bangkok",
        "start_datetime": datetime(2025, 9, 1, 14, 0),
        "end_datetime": datetime(2025, 9, 1, 18, 0),
        "event_type": "activity",
        "color": "bg-orange-500"
    },
    {
        "title": "Ferry to Koh Samui",
        "description": "Lomprayah High Speed Ferry from Chumphon",
        "location": "Chumphon Pier",
        "start_datetime": datetime(2025, 9, 2, 7, 0),
        "end_datetime": datetime(2025, 9, 2, 13, 30),
        "event_type": "transport",
        "color": "bg-cyan-500"
    },
    {
        "title": "Beach Resort Check-in",
        "description": "Four Seasons Resort Koh Samui - Ocean View Villa",
        "location": "Four Seasons Resort Koh Samui",
        "start_datetime": datetime(2025, 9, 2, 14, 0),
        "end_datetime": datetime(2025, 9, 2, 15, 0),
        "event_type": "accommodation",
        "color": "bg-green-500"
    },
    {
        "title": "Snorkeling Trip",
        "description": "Full day snorkeling at Angthong Marine Park",
        "location": "Angthong Marine Park",
        "start_datetime": datetime(2025, 9, 4, 8, 30),
        "end_datetime": datetime(2025, 9, 4, 17, 0),
        "event_type": "activity",
        "color": "bg-blue-400"
    },
    {
        "title": "Spa Appointment",
        "description": "Traditional Thai massage and aromatherapy",
        "location": "Four Seasons Spa",
        "start_datetime": datetime(2025, 9, 5, 16, 0),
        "end_datetime": datetime(2025, 9, 5, 18, 0),
        "event_type": "wellness",
        "color": "bg-pink-500"
    },
    {
        "title": "Flight to Phuket",
        "description": "Bangkok Airways connecting flight",
        "location": "Koh Samui Airport",
        "start_datetime": datetime(2025, 9, 6, 11, 0),
        "end_datetime": datetime(2025, 9, 6, 12, 15),
        "event_type": "flight",
        "color": "bg-blue-500"
    },
    {
        "title": "Sunset Dinner",
        "description": "Fine dining with ocean views",
        "location": "Mom Tri's Kitchen, Phuket",
        "start_datetime": datetime(2025, 9, 7, 18, 30),
        "end_datetime": datetime(2025, 9, 7, 21, 0),
        "event_type": "dining",
        "color": "bg-yellow-500"
    }
]

def seed_calendar_events():
    """Seed the database with mock calendar events for all users."""
    
    print("🌱 Seeding calendar events...")
    
    # Initialize database connection
    db = next(get_db())
    
    try:
        # Get all users
        users = db.query(User).all()
        
        if not users:
            print("❌ No users found. Please create users first.")
            return
        
        print(f"👥 Found {len(users)} users")
        
        for user in users:
            print(f"📅 Creating events for user: {user.email}")
            
            # Check if user already has events
            existing_events = db.query(CalendarEvent).filter(
                CalendarEvent.user_id == user.id
            ).count()
            
            if existing_events > 0:
                print(f"   ⚠️  User already has {existing_events} events, skipping...")
                continue
            
            # Create events for this user
            events_created = 0
            for event_data in MOCK_EVENTS:
                event = CalendarEvent(
                    user_id=user.id,
                    title=event_data["title"],
                    description=event_data["description"],
                    location=event_data["location"],
                    start_datetime=event_data["start_datetime"],
                    end_datetime=event_data["end_datetime"],
                    event_type=event_data["event_type"],
                    color=event_data["color"],
                    source="seeded",
                    status="confirmed"
                )
                db.add(event)
                events_created += 1
            
            db.commit()
            print(f"   ✅ Created {events_created} events for {user.email}")
        
        print("✨ Calendar events seeding completed successfully!")
        
    except Exception as e:
        print(f"❌ Error seeding calendar events: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_calendar_events()