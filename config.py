import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")

# Email Configuration
EMAIL_FROM = os.getenv("EMAIL_FROM", "onboarding@resend.dev")
EMAIL_TO = os.getenv("EMAIL_TO", "").split(",") if os.getenv("EMAIL_TO") else []

# Database Configuration
DB_PATH = os.getenv("DB_PATH", "data/listings.db")

# Search Criteria
TARGET_CONDOS = [
    condo.strip() 
    for condo in os.getenv("TARGET_CONDOS", "Flamingo Valley").split(",")
    if condo.strip()
]

# Minimum bedrooms filter
MIN_BEDROOMS = int(os.getenv("MIN_BEDROOMS", "4"))

# Simple criteria description for search queries
CRITERIA_DESC = os.getenv("CRITERIA_DESC", f"{MIN_BEDROOMS}+ bedrooms, for sale")

# Scraping Configuration
SEARCH_LIMIT = int(os.getenv("SEARCH_LIMIT", "5"))  # Number of results per search
RATE_LIMIT_DELAY = float(os.getenv("RATE_LIMIT_DELAY", "1.0"))  # Seconds between requests

# Scheduler Configuration (for cron job mode)
DAILY_RUN_TIME = os.getenv("DAILY_RUN_TIME", "08:00")  # 24-hour format HH:MM

def validate_config():
    """Validate that all required configuration is present"""
    missing = []
    
    if not FIRECRAWL_API_KEY:
        missing.append("FIRECRAWL_API_KEY")
    if not GOOGLE_API_KEY:
        missing.append("GOOGLE_API_KEY")
    if not RESEND_API_KEY:
        missing.append("RESEND_API_KEY")
    if not EMAIL_TO:
        missing.append("EMAIL_TO")
    
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            f"Please set them in your .env file or environment."
        )
    
    print("✓ Configuration validated")
    return True

def print_config():
    """Print current configuration (for debugging)"""
    print("\n" + "="*50)
    print("CONFIGURATION")
    print("="*50)
    print(f"Target Condos: {', '.join(TARGET_CONDOS)}")
    print(f"Criteria: {CRITERIA_DESC}")
    print(f"Email To: {', '.join(EMAIL_TO) if isinstance(EMAIL_TO, list) else EMAIL_TO}")
    print(f"Email From: {EMAIL_FROM}")
    print(f"Database: {DB_PATH}")
    print(f"Search Limit: {SEARCH_LIMIT} results per query")
    print(f"Rate Limit Delay: {RATE_LIMIT_DELAY}s")
    print("="*50 + "\n")

# Auto-validate on import (comment out if you want manual validation)
# validate_config()
