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
                    
                    res = response[0] if isinstance(response, tuple) else response
                    
                    items = []
                    if isinstance(res, dict):
                        items = res.get('web') or res.get('data') or []
                    else:
                        items = getattr(res, 'web', getattr(res, 'data', []))
                    
                    if not items:
                        print(f"No results found for {condo} on {site}")
                        continue
                
                    print(f"Processing {len(items)} items for {condo}...")

                    for item in items:
                        # Detect if item is a Document object or a dictionary
                        if hasattr(item, 'markdown'):
                            raw_content = item.markdown
                            url = item.url
                        elif isinstance(item, dict):
                            raw_content = item.get('markdown') or item.get('content')
                            url = item.get('url')
                        else:
                            continue

                        if not raw_content or not url:
                            continue

                        extracted_data = parse_with_llm(raw_content, url, condo)
                        
                        if extracted_data:
                            extracted_data['scraped_at'] = datetime.datetime.now().isoformat()
                            db.save_listing(extracted_data)
                            print(f"Successfully saved: {url}")
                    
                    # Brief pause to respect rate limits between site searches
                    time.sleep(1)
                            
                except Exception as e:
                    print(f"Error scraping {condo} on {site}: {e}")
                
        # Send Email Digest
        send_digest()
        
    except Exception as e:
        print(f"Critical Job Error: {e}")
    finally:
        IS_SCRAPING = False
        print(f"--- Job Finished: {datetime.datetime.now()} ---")

def start_manual_job_async():
    """Starts the job in a separate thread so it doesn't block the web request"""
    if IS_SCRAPING:
        return False, "Job is already running."
    
    thread = threading.Thread(target=run_scraper_job)
    thread.start()
    return True, "Scraping started in background. Refresh in a few minutes."

def parse_with_llm(markdown_text, url, condo_hint):
    prompt = f"""
    You are a real estate data extractor. 
    Analyze the following markdown text from a property listing ({url}).
    Extract the following fields into a valid JSON object.
    
    Fields:
    - platform: "propertyguru" or "99.co" (infer from url)
    - listing_id: unique id from the platform
    - url: {url}
    - condo_name: standardized name (inferred from text or "{condo_hint}")
    - address: string
    - district: string (e.g. D10)
    - price_sgd: integer (no symbols)
    - price_psf: integer (no symbols)
    - bedrooms: integer
    - bathrooms: integer
    - size_sqft: integer
    - floor_level: string (e.g. "High", "Low", "12")
    - tenure: string
    - top_year: integer (TOP year)
    - agent_name: string
    - agent_phone: string
    - listing_date: string (ISO format if possible, else raw)
    
    If a field is not found, return null. 
    Strictly return ONLY the JSON object. No markdown formatting.
    
    Text content:
    {markdown_text}
    """
    
    try:
        response = genai_client.models.generate_content(
          model=model,
          contents=prompt,
        )
        # Clean response if model adds markdown blocks
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        print(f"LLM parse error for {url}: {e}")
        return None

def send_digest():
    new_listings = db.get_unsent_listings()
    if not new_listings:
        print("No new listings to email.")
        return

    print(f"Sending email for {len(new_listings)} listings...")
    
    rows = ""
    for l in new_listings:
        rows += f"""
        <tr>
            <td style="padding:8px; border-bottom:1px solid #ddd;">{l['condo_name']}</td>
            <td style="padding:8px; border-bottom:1px solid #ddd;">${l['price_sgd']:,}</td>
            <td style="padding:8px; border-bottom:1px solid #ddd;">{l['bedrooms']} Bed</td>
            <td style="padding:8px; border-bottom:1px solid #ddd;"><a href="{l['url']}">Link</a></td>
        </tr>
        """
    
    html_content = f"""
    <h2>Property Digest</h2>
    <table style="width:100%; text-align:left; border-collapse:collapse;">
        <thead>
            <tr style="background:#f4f4f4;">
                <th style="padding:8px;">Condo</th>
                <th style="padding:8px;">Price</th>
                <th style="padding:8px;">Config</th>
                <th style="padding:8px;">Link</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    """
    
    try:
        resend.api_key = config.RESEND_API_KEY
        resend.Emails.send({
            "from": config.EMAIL_FROM,
            "to": config.EMAIL_TO,
            "subject": f"New Property Listings: ({len(new_listings)})",
            "html": html_content
        })
        
        db.mark_as_sent([l['id'] for l in new_listings])
        print("Email sent successfully.")
    except Exception as e:
        print(f"Email error: {e}")
