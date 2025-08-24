#!/usr/bin/env python3
"""
Seed document categories for the application
"""

from database import SessionLocal, Base
from sqlalchemy import Column, Integer, String, JSON, DateTime, func

class DocumentCategory(Base):
    __tablename__ = "document_categories"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    keywords = Column(JSON, nullable=True)
    extraction_fields = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

def seed_categories():
    """Create initial document categories"""
    
    categories = [
        {
            "name": "Flight Booking",
            "keywords": ["flight", "airline", "boarding pass", "departure", "arrival", "gate", "seat"],
            "extraction_fields": {
                "flight_number": "text",
                "departure_date": "date",
                "departure_airport": "text",
                "arrival_airport": "text",
                "passenger_name": "text",
                "booking_reference": "text",
                "total_cost": "currency"
            }
        },
        {
            "name": "Hotel Reservation", 
            "keywords": ["hotel", "accommodation", "reservation", "check-in", "check-out", "room"],
            "extraction_fields": {
                "hotel_name": "text",
                "check_in_date": "date",
                "check_out_date": "date", 
                "room_type": "text",
                "guest_name": "text",
                "confirmation_number": "text",
                "total_cost": "currency"
            }
        },
        {
            "name": "Restaurant Receipt",
            "keywords": ["restaurant", "receipt", "meal", "dining", "cafe", "food"],
            "extraction_fields": {
                "restaurant_name": "text",
                "date": "date",
                "time": "time", 
                "location": "text",
                "total_amount": "currency",
                "payment_method": "text"
            }
        },
        {
            "name": "Tour Booking",
            "keywords": ["tour", "excursion", "activity", "guide", "sightseeing"],
            "extraction_fields": {
                "tour_name": "text",
                "date": "date",
                "time": "time",
                "duration": "text",
                "location": "text",
                "provider": "text",
                "total_cost": "currency"
            }
        },
        {
            "name": "Transport Ticket",
            "keywords": ["train", "bus", "taxi", "uber", "transport", "ticket"],
            "extraction_fields": {
                "transport_type": "text",
                "departure_location": "text",
                "arrival_location": "text",
                "departure_date": "date",
                "departure_time": "time",
                "ticket_number": "text",
                "total_cost": "currency"
            }
        },
        {
            "name": "Visa Document",
            "keywords": ["visa", "passport", "immigration", "embassy", "consulate"],
            "extraction_fields": {
                "document_type": "text",
                "country": "text",
                "validity_period": "text",
                "issue_date": "date",
                "expiry_date": "date",
                "document_number": "text"
            }
        },
        {
            "name": "Travel Insurance",
            "keywords": ["insurance", "coverage", "policy", "medical", "travel protection"],
            "extraction_fields": {
                "policy_number": "text",
                "provider": "text",
                "coverage_period": "text",
                "start_date": "date",
                "end_date": "date",
                "total_premium": "currency"
            }
        },
        {
            "name": "Other",
            "keywords": [],
            "extraction_fields": {
                "document_type": "text",
                "date": "date",
                "description": "text",
                "amount": "currency"
            }
        }
    ]
    
    db = SessionLocal()
    
    try:
        print("🌱 Seeding document categories...")
        
        for cat_data in categories:
            # Check if category already exists
            existing = db.query(DocumentCategory).filter(
                DocumentCategory.name == cat_data["name"]
            ).first()
            
            if not existing:
                category = DocumentCategory(
                    name=cat_data["name"],
                    keywords=cat_data["keywords"],
                    extraction_fields=cat_data["extraction_fields"]
                )
                db.add(category)
                print(f"  ✅ Added category: {cat_data['name']}")
            else:
                print(f"  ⏭️  Category already exists: {cat_data['name']}")
        
        db.commit()
        print(f"\n✅ Successfully seeded {len(categories)} document categories!")
        
    except Exception as e:
        print(f"❌ Error seeding categories: {e}")
        db.rollback()
    
    finally:
        db.close()

if __name__ == "__main__":
    seed_categories()