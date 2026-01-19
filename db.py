import sqlite3
from sqlite_utils import Database
from config import DB_PATH
import os

def get_db():
    """Get database connection with proper directory creation"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return Database(sqlite3.connect(DB_PATH))

def init_db():
    """Initialize database with schema if not exists"""
    db = get_db()
    
    if "listings" in db.table_names():
        return
    
    # Create table with proper schema
    db["listings"].create({
        "platform": str,
        "listing_id": str,
        "url": str,
        "condo_name": str,
        "address": str,
        "district": str,
        "price_sgd": int,
        "price_psf": int,
        "bedrooms": int,
        "bathrooms": int,
        "size_sqft": int,
        "floor_level": str,
        "tenure": str,
        "top_year": int,
        "agent_name": str,
        "agent_phone": str,
        "listing_date": str,
        "scraped_at": str,
        "is_sent": int  # 0 = not sent, 1 = sent
    }, pk="id", not_null={"listing_id", "platform"})
    
    # Create unique index on listing_id + platform to prevent duplicates
    db["listings"].create_index(["listing_id", "platform"], unique=True, if_not_exists=True)
    
    # Create index on is_sent for faster queries
    db["listings"].create_index(["is_sent"], if_not_exists=True)
    
    print("✓ Database initialized")

def save_listing(data):
    """Save or update a single listing"""
    db = get_db()
    try:
        # Ensure is_sent defaults to 0 for new listings
        if 'is_sent' not in data:
            data['is_sent'] = 0
            
        db["listings"].upsert(data, pk=["listing_id", "platform"])
        print(f"DB: Saved {data.get('condo_name', 'Unknown')} ({data.get('listing_id')})")
    except Exception as e:
        print(f"Database save error: {e}")

def save_listings_batch(listings_data):
    """Save multiple listings at once (more efficient)"""
    if not listings_data:
        return
    
    db = get_db()
    try:
        # Ensure all listings have is_sent = 0 by default
        for listing in listings_data:
            if 'is_sent' not in listing:
                listing['is_sent'] = 0
        
        # Use upsert_all for batch operations
        db["listings"].upsert_all(
            listings_data, 
            pk=["listing_id", "platform"],
            alter=True  # Auto-add columns if schema changes
        )
        print(f"✓ Batch saved {len(listings_data)} listings")
    except Exception as e:
        print(f"Batch save error: {e}")
        import traceback
        traceback.print_exc()

def get_unsent_listings():
    """Get all listings that haven't been emailed yet"""
    db = get_db()
    try:
        return list(db["listings"].rows_where("is_sent = 0", order_by="scraped_at desc"))
    except Exception as e:
        print(f"Error fetching unsent listings: {e}")
        return []

def mark_as_sent(listing_ids):
    """Mark listings as sent by their IDs"""
    if not listing_ids:
        return
    
    db = get_db()
    try:
        for lid in listing_ids:
            db["listings"].update(lid, {"is_sent": 1})
        print(f"✓ Marked {len(listing_ids)} listings as sent")
    except Exception as e:
        print(f"Error marking as sent: {e}")

def get_all_listings(limit=100):
    """Get all listings ordered by most recent first"""
    db = get_db()
    try:
        return list(db["listings"].rows_where(
            order_by="scraped_at desc",
            limit=limit
        ))
    except Exception as e:
        print(f"Error fetching all listings: {e}")
        return []

def get_listing_count():
    """Get total count of listings"""
    db = get_db()
    try:
        return db.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
    except Exception:
        return 0

def get_stats():
    """Get database statistics"""
    db = get_db()
    try:
        total = db.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
        unsent = db.execute("SELECT COUNT(*) FROM listings WHERE is_sent = 0").fetchone()[0]
        platforms = db.execute("""
            SELECT platform, COUNT(*) as count 
            FROM listings 
            GROUP BY platform
        """).fetchall()
        
        return {
            "total": total,
            "unsent": unsent,
            "by_platform": {p[0]: p[1] for p in platforms}
        }
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {"total": 0, "unsent": 0, "by_platform": {}}
