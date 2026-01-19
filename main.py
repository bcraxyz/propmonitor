from fasthtml.common import *
from apscheduler.schedulers.background import BackgroundScheduler
import agent
import db
import os

# 1. Setup Scheduler (Daily Auto-Run)
# We still keep the scheduler for daily automation
if os.getenv("RUN_ON_STARTUP"):
    agent.start_manual_job_async()

scheduler = BackgroundScheduler()
scheduler.add_job(agent.run_scraper_job, 'interval', hours=24)
scheduler.start()

# 2. Setup FastHTML App
app, rt = fast_app(
    hdrs=(Script(src="https://cdn.tailwindcss.com"),),
    title="PropMonitor"
)

def format_currency(val):
    return f"${val:,}" if val else "-"

@rt("/")
def get():
    listings = db.get_all_listings()
    
    return Body(cls="bg-gray-50 min-h-screen p-8")(
        Div(cls="max-w-7xl mx-auto")(
            # Header with Button
            Div(cls="flex justify-between items-center mb-8")(
                Div(
                    H1("Property Monitor", cls="text-3xl font-bold text-gray-800"),
                    Span(f"Total Listings: {len(listings)}", cls="ml-2 bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-medium")
                ),
                # THE TRIGGER BUTTON
                Form(method="post", action="/trigger", hx_post="/trigger", hx_swap="none")(
                    Button("Run Scraper Now", 
                           cls="bg-black text-white px-4 py-2 rounded hover:bg-gray-800 transition shadow-sm",
                           onclick="alert('Scraper started in background! Check logs or refresh in a few mins.')")
                )
            ),
            
            # Table Container
            Div(cls="bg-white rounded-lg shadow overflow-x-auto")(
                Table(cls="min-w-full divide-y divide-gray-200")(
                    Thead(cls="bg-gray-50")(
                        Tr(
                            Th("Condo", cls="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"),
                            Th("Price", cls="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"),
                            Th("PSF", cls="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"),
                            Th("Config", cls="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"),
                            Th("Size", cls="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"),
                            Th("Platform", cls="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"),
                            Th("Action", cls="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"),
                        )
                    ),
                    Tbody(cls="bg-white divide-y divide-gray-200")(
                        *[Tr(cls="hover:bg-gray-50")(
                            Td(l['condo_name'], cls="px-6 py-4 whitespace-nowrap font-medium text-gray-900"),
                            Td(format_currency(l['price_sgd']), cls="px-6 py-4 whitespace-nowrap text-green-600 font-semibold"),
                            Td(format_currency(l['price_psf']), cls="px-6 py-4 whitespace-nowrap text-gray-500"),
                            Td(f"{l['bedrooms']} Bed / {l['bathrooms']} Bath", cls="px-6 py-4 whitespace-nowrap text-gray-500"),
                            Td(f"{l['size_sqft']} sqft", cls="px-6 py-4 whitespace-nowrap text-gray-500"),
                            Td(
                                Span(l['platform'], cls=f"px-2 inline-flex text-xs leading-5 font-semibold rounded-full {'bg-red-100 text-red-800' if 'guru' in l['platform'] else 'bg-blue-100 text-blue-800'}")
                            ),
                            Td(
                                A("View", href=l['url'], target="_blank", cls="text-indigo-600 hover:text-indigo-900 font-medium")
                            )
                        ) for l in listings]
                    )
                )
            )
        )
    )

@rt("/trigger")
def post():
    success, msg = agent.start_manual_job_async()
    print(f"Manual Trigger: {msg}")
    return Response(status_code=204) # 204 No Content keeps the page as-is

serve()
