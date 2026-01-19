import time
import json
import datetime
import threading
from firecrawl import FirecrawlApp
import google.genai as genai
import resend
import config
import db

# Global Lock to prevent multiple simultaneous scrapes
IS_SCRAPING = False

# Initialize Clients
firecrawl = FirecrawlApp(api_key=config.FIRECRAWL_API_KEY)
genai_client = genai.Client(api_key=config.GOOGLE_API_KEY)
model = 'gemini-2.5-flash'

def run_scraper_job():
    global IS_SCRAPING
    if IS_SCRAPING:
        print("Job already running. Skipping...")
        return
    
    IS_SCRAPING = True
    print(f"--- Starting Job: {datetime.datetime.now()} ---")
    
    try:
        db.init_db()
        batch = []  # Collect all listings for batch insert
        
        for condo in config.TARGET_CONDOS:
            for site in ["propertyguru.com.sg", "99.co"]:
                print(f"Scraping for {condo} on {site}...")
                
                query = f"site:{site} {condo} {config.CRITERIA_DESC}"
                
                try:
                    response = firecrawl.search(
                        query, 
                        limit=5,
                        scrape_options={"formats": ["markdown"]}
                    )
                    
                    # Handle response - it's a tuple (result, metadata) or just result
                    res = response[0] if isinstance(response, tuple) else response
                    
                    # Extract items from response
                    items = []
                    if isinstance(res, dict):
                        items = res.get('web', []) or res.get('data', [])
                    else:
                        items = getattr(res, 'web', []) or getattr(res, 'data', [])
                    
                    if not items:
                        print(f"No results found for {condo} on {site}")
                        continue
                
                    print(f"Processing {len(items)} items for {condo}...")

                    for idx, item in enumerate(items):
                        # Check for errors in metadata first
                        if isinstance(item, dict):
                            metadata = item.get('metadata', {})
                            if metadata.get('error') or metadata.get('statusCode', 200) >= 400:
                                print(f"Skipping item {idx+1}: {metadata.get('error', 'Unknown error')}")
                                continue
                            
                            raw_content = item.get('markdown') or item.get('content', '')
                            url = item.get('url', '')
                        else:
                            # Handle Document-like objects
                            raw_content = getattr(item, 'markdown', '') or getattr(item, 'content', '')
                            url = getattr(item, 'url', '')

                        if not raw_content or not url:
                            print(f"Skipping item {idx+1}: missing content or URL")
                            continue

                        extracted_data = parse_with_llm(raw_content, url, condo)
                        
                        if extracted_data and extracted_data.get('listing_id'):
                            extracted_data['scraped_at'] = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
                            batch.append(extracted_data)
                            print(f"✓ Extracted: {extracted_data.get('condo_name', 'Unknown')} - {url[:60]}...")
                    
                    # Brief pause to respect rate limits
                    time.sleep(1)
                            
                except Exception as e:
                    print(f"Error scraping {condo} on {site}: {e}")
        
        # Batch save all listings
        if batch:
            db.save_listings_batch(batch)
            print(f"\n✓ Saved {len(batch)} listings to database")
        else:
            print("\nNo listings extracted")
        
        # Send Email Digest
        send_digest()
        
    except Exception as e:
        print(f"Critical Job Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        IS_SCRAPING = False
        print(f"--- Job Finished: {datetime.datetime.now()} ---\n")

def start_manual_job_async():
    """Starts the job in a separate thread so it doesn't block the web request"""
    if IS_SCRAPING:
        return False, "Job is already running."
    
    thread = threading.Thread(target=run_scraper_job, daemon=True)
    thread.start()
    return True, "Scraping started in background. Refresh in a few minutes."

def parse_with_llm(markdown_text, url, condo_hint):
    """Extract structured property data using Gemini with optimized prompt"""
    prompt = f"""Extract property listing data from this markdown content as JSON.

    Required fields (use null if not found):
    - platform: "propertyguru" or "99co" (infer from URL)
    - listing_id: unique identifier from the platform (extract from URL or content)
    - url: {url}
    - condo_name: standardized name (from content or use: "{condo_hint}")
    - address: full address string
    - district: district code (e.g., "D15", "District 15")
    - price_sgd: integer price in SGD (remove $ and commas)
    - price_psf: integer price per sqft (remove $ and commas)
    - bedrooms: integer number of bedrooms
    - bathrooms: integer number of bathrooms
    - size_sqft: integer size in square feet
    - floor_level: string (e.g., "High", "Mid", "Low", "12th")
    - tenure: string (e.g., "Freehold", "99-year leasehold")
    - top_year: integer year of completion/TOP
    - agent_name: string agent name
    - agent_phone: string agent phone number
    - listing_date: string listing date (ISO format YYYY-MM-DD if possible)
    
    URL: {url}
    Condo: {condo_hint}
    
    Content:
    {markdown_text}
    
    Return ONLY valid JSON with the fields above. No markdown formatting."""
    
    try:
        response = genai_client.models.generate_content(
            model=model,
            contents=prompt,
        )
        
        # Clean response - remove markdown code blocks if present
        clean_json = response.text.strip()
        clean_json = clean_json.replace("```json", "").replace("```", "").strip()
        
        data = json.loads(clean_json)
        
        # Ensure required fields exist
        if not data.get('listing_id'):
            # Try to extract from URL as fallback
            parts = url.rstrip('/').split('/')
            data['listing_id'] = parts[-1] if parts else f"unknown_{hash(url)}"
        
        return data
        
    except json.JSONDecodeError as e:
        print(f"JSON parse error for {url[:60]}: {e}")
        print(f"Response was: {response.text[:200]}")
        return None
    except Exception as e:
        print(f"LLM parse error for {url[:60]}: {e}")
        return None

def send_digest():
    """Send email digest of new listings"""
    new_listings = db.get_unsent_listings()
    if not new_listings:
        print("No new listings to email.")
        return

    print(f"📧 Sending email for {len(new_listings)} listings...")
    
    # Generate table rows
    rows = "".join([
        f"""<tr style="border-bottom: 1px solid #e5e7eb;">
            <td style="padding: 12px 16px; font-weight: 600; color: #1e293b;">{l['condo_name']}</td>
            <td style="padding: 12px 16px; color: #059669; font-weight: 700;">${l['price_sgd']:,}</td>
            <td style="padding: 12px 16px; color: #64748b; font-size: 14px;">{l['bedrooms']}BR / {l['bathrooms']}BA</td>
            <td style="padding: 12px 16px; color: #64748b; font-size: 14px;">{l['size_sqft']:,} sqft</td>
            <td style="padding: 12px 16px; color: #64748b; font-size: 13px;">{l.get('district', 'N/A')}</td>
            <td style="padding: 12px 16px;">
                <a href="{l['url']}" style="color: #4f46e5; text-decoration: none; font-weight: 600; font-size: 14px;">
                    View Listing →
                </a>
            </td>
        </tr>"""
        for l in new_listings
    ])
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px;">
    <div style="max-width: 900px; margin: 0 auto; background-color: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.07);">
        
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; color: white;">
            <h1 style="margin: 0; font-size: 28px; font-weight: 800;">🏠 Property Digest</h1>
            <p style="margin: 8px 0 0 0; opacity: 0.95; font-size: 15px;">
                {len(new_listings)} new listing{"s" if len(new_listings) != 1 else ""} found • {datetime.datetime.now().strftime('%B %d, %Y')}
            </p>
        </div>
        
        <!-- Table -->
        <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; text-align: left;">
                <thead>
                    <tr style="background-color: #f1f5f9; border-bottom: 2px solid #e2e8f0;">
                        <th style="padding: 14px 16px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #475569;">Condo</th>
                        <th style="padding: 14px 16px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #475569;">Price</th>
                        <th style="padding: 14px 16px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #475569;">Config</th>
                        <th style="padding: 14px 16px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #475569;">Size</th>
                        <th style="padding: 14px 16px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #475569;">District</th>
                        <th style="padding: 14px 16px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #475569;">Link</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
        
        <!-- Footer -->
        <div style="padding: 24px; background-color: #f8fafc; border-top: 1px solid #e2e8f0; text-align: center;">
            <p style="margin: 0; color: #64748b; font-size: 13px;">
                Property Monitor • Automated Daily Digest
            </p>
        </div>
        
    </div>
</body>
</html>"""
    
    try:
        resend.api_key = config.RESEND_API_KEY
        resend.Emails.send({
            "from": config.EMAIL_FROM,
            "to": config.EMAIL_TO,
            "subject": f"🏠 New Property Listings ({len(new_listings)})",
            "html": html_content
        })
        
        db.mark_as_sent([l['id'] for l in new_listings])
        print("✓ Email sent successfully")
    except Exception as e:
        print(f"✗ Email error: {e}")
        import traceback
        traceback.print_exc()
