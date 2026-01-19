from fasthtml.common import *
from datetime import datetime
import agent, db, config

# Initialize FastHTML app with Tailwind CSS
app, rt = fast_app(
    hdrs=(
        Script(src="https://cdn.tailwindcss.com"),
        Style("""
            @keyframes pulse-slow {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            .scraping { animation: pulse-slow 2s ease-in-out infinite; }
        """)
    ),
    title="Property Monitor"
)

# Helper functions
def format_curr(val): 
    return f"${val:,}" if val else "-"

def format_date(date_str):
    if not date_str: 
        return "-"
    try: 
        return datetime.fromisoformat(date_str).strftime("%b %d, %H:%M")
    except: 
        return date_str

def platform_badge(platform):
    """Create a colored badge for the platform"""
    if 'guru' in platform.lower():
        return Span(
            "PropertyGuru", 
            cls="px-2 py-1 rounded-md text-xs font-bold uppercase bg-red-100 text-red-700"
        )
    elif '99' in platform:
        return Span(
            "99.co", 
            cls="px-2 py-1 rounded-md text-xs font-bold uppercase bg-blue-100 text-blue-700"
        )
    else:
        return Span(
            platform, 
            cls="px-2 py-1 rounded-md text-xs font-bold uppercase bg-gray-100 text-gray-700"
        )

@rt("/")
def get():
    """Main page with listings table"""
    db.init_db()
    listings = db.get_all_listings(limit=200)
    stats = db.get_stats()
    
    return Body(cls="bg-gradient-to-br from-slate-50 to-slate-100 min-h-screen font-sans text-gray-900")(
        Div(cls="max-w-[1600px] mx-auto p-4 md:p-8")(
            
            # Header Section
            Header(cls="mb-8")(
                Div(cls="flex flex-col md:flex-row justify-between items-start md:items-center gap-4")(
                    # Title and Stats
                    Div(
                        H1("🏠 Property Monitor", cls="text-4xl font-extrabold tracking-tight text-slate-800"),
                        Div(cls="flex gap-4 mt-2 text-sm")(
                            P(f"Total: {stats['total']} listings", cls="text-slate-600 font-medium"),
                            P(f"Unsent: {stats['unsent']}", cls="text-indigo-600 font-bold"),
                            P(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", cls="text-slate-500")
                        )
                    ),
                    
                    # Action Buttons
                    Div(cls="flex gap-3")(
                        Form(hx_post="/trigger", hx_swap="none", cls="inline")(
                            Button(
                                "🔄 Scrape Now",
                                id="scrape-btn",
                                cls="bg-indigo-600 text-white px-6 py-3 rounded-lg font-bold hover:bg-indigo-700 transition-all shadow-lg hover:shadow-xl active:scale-95",
                                onclick="this.innerText='⏳ Scraping...'; this.classList.add('scraping'); setTimeout(() => location.reload(), 60000);"
                            )
                        ),
                        A(
                            "🔧 Config",
                            href="/config",
                            cls="bg-slate-600 text-white px-6 py-3 rounded-lg font-bold hover:bg-slate-700 transition-all shadow-lg hover:shadow-xl"
                        )
                    )
                )
            ),
            
            # Empty state or table
            (
                Div(cls="bg-white rounded-2xl shadow-xl p-16 text-center")(
                    H2("No listings yet", cls="text-2xl font-bold text-slate-700 mb-4"),
                    P("Click 'Scrape Now' to start collecting property listings", cls="text-slate-500 mb-6"),
                    Form(hx_post="/trigger", hx_swap="none")(
                        Button(
                            "Start Scraping",
                            cls="bg-indigo-600 text-white px-8 py-3 rounded-lg font-bold hover:bg-indigo-700 transition-all"
                        )
                    )
                ) if not listings else
                
                # Listings Table
                Div(cls="bg-white shadow-2xl rounded-2xl overflow-hidden border border-gray-200")(
                    Div(cls="overflow-x-auto")(
                        Table(cls="w-full text-left border-collapse")(
                            Thead(cls="bg-slate-800 text-slate-200 text-xs uppercase tracking-wider font-semibold sticky top-0")(
                                Tr(
                                    Th("Platform", cls="p-4 whitespace-nowrap"),
                                    Th("Property", cls="p-4 whitespace-nowrap"),
                                    Th("Price", cls="p-4 whitespace-nowrap"),
                                    Th("PSF", cls="p-4 whitespace-nowrap"),
                                    Th("Layout", cls="p-4 whitespace-nowrap"),
                                    Th("Size", cls="p-4 whitespace-nowrap"),
                                    Th("Floor", cls="p-4 whitespace-nowrap"),
                                    Th("Tenure", cls="p-4 whitespace-nowrap"),
                                    Th("Agent", cls="p-4 whitespace-nowrap"),
                                    Th("Scraped", cls="p-4 whitespace-nowrap"),
                                    Th("", cls="p-4 text-right whitespace-nowrap"),
                                )
                            ),
                            Tbody(
                                *[Tr(cls="border-b border-gray-100 hover:bg-indigo-50/40 transition-colors")(
                                    # Platform
                                    Td(platform_badge(l['platform']), cls="p-4"),
                                    
                                    # Property Info
                                    Td(cls="p-4")(
                                        Div(l['condo_name'] or "Unknown", cls="font-bold text-slate-800 text-sm"),
                                        Div(cls="text-xs text-slate-500 mt-1")(
                                            f"{l.get('district', 'N/A')} • {l.get('address', 'No address')[:40]}..."
                                        )
                                    ),
                                    
                                    # Price
                                    Td(
                                        Div(format_curr(l['price_sgd']), cls="text-emerald-600 font-bold text-base"),
                                        cls="p-4 whitespace-nowrap"
                                    ),
                                    
                                    # PSF
                                    Td(
                                        format_curr(l['price_psf']) if l.get('price_psf') else "-", 
                                        cls="p-4 text-gray-600 font-mono text-sm whitespace-nowrap"
                                    ),
                                    
                                    # Layout
                                    Td(
                                        f"{l['bedrooms']}BR / {l['bathrooms']}BA" if l.get('bedrooms') and l.get('bathrooms') else "-",
                                        cls="p-4 text-sm whitespace-nowrap"
                                    ),
                                    
                                    # Size
                                    Td(
                                        f"{l['size_sqft']:,}" if l.get('size_sqft') else "-",
                                        cls="p-4 text-sm font-medium whitespace-nowrap"
                                    ),
                                    
                                    # Floor
                                    Td(
                                        l.get('floor_level', '-'),
                                        cls="p-4 text-xs text-gray-500 whitespace-nowrap"
                                    ),
                                    
                                    # Tenure
                                    Td(cls="p-4 whitespace-nowrap")(
                                        Div(l.get('tenure', '-'), cls="text-xs leading-tight"),
                                        Div(f"TOP: {l.get('top_year', '-')}", cls="text-xs font-bold text-indigo-600 mt-1")
                                    ),
                                    
                                    # Agent
                                    Td(cls="p-4 whitespace-nowrap")(
                                        Div(l.get('agent_name', '-'), cls="text-xs font-bold"),
                                        Div(l.get('agent_phone', '-'), cls="text-xs text-gray-500 mt-1")
                                    ),
                                    
                                    # Scraped At
                                    Td(
                                        format_date(l.get('scraped_at')),
                                        cls="p-4 text-xs text-gray-400 whitespace-nowrap"
                                    ),
                                    
                                    # Action
                                    Td(cls="p-4 text-right whitespace-nowrap")(
                                        A(
                                            "View Listing →",
                                            href=l['url'],
                                            target="_blank",
                                            cls="text-indigo-600 hover:text-indigo-900 font-bold text-xs hover:underline"
                                        )
                                    )
                                ) for l in listings]
                            )
                        )
                    )
                )
            ),
            
            # Footer
            Footer(cls="mt-8 text-center text-sm text-slate-500")(
                P(f"Monitoring: {', '.join(config.TARGET_CONDOS)} • {config.CRITERIA_DESC}")
            )
        )
    )

@rt("/config")
def get():
    """Configuration page"""
    return Body(cls="bg-gradient-to-br from-slate-50 to-slate-100 min-h-screen font-sans p-8")(
        Div(cls="max-w-2xl mx-auto")(
            Div(cls="bg-white rounded-2xl shadow-xl p-8")(
                H1("⚙️ Configuration", cls="text-3xl font-bold text-slate-800 mb-6"),
                
                Div(cls="space-y-4 mb-8")(
                    Div(
                        H3("Target Condominiums", cls="font-bold text-slate-700 mb-2"),
                        Ul(*[Li(condo, cls="text-slate-600") for condo in config.TARGET_CONDOS])
                    ),
                    Div(
                        H3("Search Criteria", cls="font-bold text-slate-700 mb-2"),
                        P(config.CRITERIA_DESC, cls="text-slate-600")
                    ),
                    Div(
                        H3("Email Recipients", cls="font-bold text-slate-700 mb-2"),
                        P(", ".join(config.EMAIL_TO) if isinstance(config.EMAIL_TO, list) else config.EMAIL_TO, 
                          cls="text-slate-600")
                    ),
                    Div(
                        H3("Database", cls="font-bold text-slate-700 mb-2"),
                        P(config.DB_PATH, cls="text-slate-600 font-mono text-sm")
                    )
                ),
                
                A(
                    "← Back to Listings",
                    href="/",
                    cls="inline-block bg-slate-600 text-white px-6 py-3 rounded-lg font-bold hover:bg-slate-700 transition-all"
                )
            )
        )
    )

@rt("/trigger")
def post():
    """Trigger manual scrape job"""
    success, message = agent.start_manual_job_async()
    return Response(status_code=204 if success else 409)

@rt("/health")
def get():
    """Health check endpoint for Railway"""
    try:
        db.init_db()
        stats = db.get_stats()
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "listings_count": stats['total'],
            "unsent_count": stats['unsent']
        }
    except Exception as e:
        return Response(
            content={"status": "unhealthy", "error": str(e)},
            status_code=500
        )

# Start the server
serve()
