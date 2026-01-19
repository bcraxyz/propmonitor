import sqlite3
from sqlite_utils import Database
from config import DB_PATH
import os

def get_db():
    # Ensure data directory exists for Railway Volume
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return Database(sqlite3.connect(DB_PATH))

def init_db():
    db = get_db()
    # Create table if not exists with correct schema
    if "listings" not in db.table_names():
        db["listings"].create({
            "id": int,
            "platform": str, # propertyguru or 99
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
            "is_sent": int # 0 or 1
        }, pk="id")
        # specific composite key to avoid duplicates
        db["listings"].create_index(["listing_id", "platform"], unique=True)

def save_listing(data):
    db = get_db()
    try:
        # listing_id and platform together must be unique
        db["listings"].upsert(data, pk=["listing_id", "platform"])
        print(f"DB Update: Saved {data.get('condo_name')} ({data.get('listing_id')})")
    except Exception as e:
        print(f"Database Error: {e}")

def get_unsent_listings():
    db = get_db()
    return list(db["listings"].rows_where("is_sent = 0"))

def mark_as_sent(listing_ids):
    db = get_db()
    for lid in listing_ids:
        db["listings"].update(lid, {"is_sent": 1})

def get_all_listings():
    db = get_db()
    return list(db["listings"].rows_where(order_by="scraped_at desc"))
