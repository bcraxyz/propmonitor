import os
from dotenv import load_dotenv

load_dotenv()

# Secrets
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO")

# Application Settings
DB_PATH = os.getenv("DB_PATH", "data/listings.db")

# Search Criteria
TARGET_CONDOS = [
    "Flamingo Valley",
    "Mandarin Gardens"
    # Add more condo names here
]

# Simple criteria string to guide the LLM
CRITERIA_DESC = "4+ bedrooms, for sale"
