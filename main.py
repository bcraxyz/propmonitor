from fasthtml.common import *
from datetime import datetime
import agent, db, os

app, rt = fast_app(
    hdrs=(Script(src="https://cdn.tailwindcss.com"),),
    title="Property Monitor"
)

def format_curr(val): return f"${val:,}" if val else "-"
def format_date(date_str):
    if not date_str: return "-"
    try: return datetime.fromisoformat(date_str).strftime("%b %d, %H:%M")
    except: return date_str

@rt("/")
def get():
    listings = db.get_all_listings()
    
    return Body(cls="bg-gray-100 font-sans text-gray-900")(
        Div(cls="max-w-[1600px] mx-auto p-4 md:p-8")(
            # Header Section
            Header(cls="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4")(
                Div(
                    H1("Property Monitor", cls="text-3xl font-extrabold tracking-tight text-slate-800"),
                    P(f"Database synced: {datetime.now().strftime('%Y-%m-%d %H:%M')}", cls="text-slate-500 text-sm font-medium")
                ),
                Div(cls="flex gap-3")(
                    Form(hx_post="/trigger", hx_swap="none")(
                        Button("Scrape Now", 
                               cls="bg-indigo-600 text-white px-6 py-2.5 rounded-lg font-bold hover:bg-indigo-700 transition shadow-lg active:scale-95",
                               onclick="this.innerText='Agent Running...';")
                    )
                )
            ),
            
            # The Main Data Grid
            Div(cls="bg-white shadow-2xl rounded-2xl overflow-hidden border border-gray-200")(
                Div(cls="overflow-x-auto")(
                    Table(cls="w-full text-left border-collapse table-auto")(
                        Thead(cls="bg-slate-800 text-slate-200 text-xs uppercase tracking-wider font-semibold")(
                            Tr(
                                Th("Platform", cls="p-4"),
                                Th("Condo / Address", cls="p-4"),
                                Th("Price", cls="p-4"),
                                Th("PSF", cls="p-4"),
                                Th("Beds/Baths", cls="p-4"),
                                Th("Size (sqft)", cls="p-4"),
                                Th("Floor", cls="p-4"),
                                Th("Tenure/TOP", cls="p-4"),
                                Th("Agent Info", cls="p-4"),
                                Th("Scraped At", cls="p-4"),
                                Th("Link", cls="p-4 text-right"),
                            )
                        ),
                        Tbody(
                            *[Tr(cls="border-b border-gray-100 hover:bg-indigo-50/30 transition-colors")(
                                # Platform Badge
                                Td(Span(l['platform'], cls=f"px-2 py-1 rounded text-[10px] font-bold uppercase {'bg-red-100 text-red-700' if 'guru' in l['platform'] else 'bg-blue-100 text-blue-700'}"), cls="p-4"),
                                
                                # Condo & Address
                                Td(Div(cls="font-bold text-slate-800")(l['condo_name']), 
                                   Div(cls="text-xs text-slate-500 truncate max-w-[200px]")(f"{l['district']} - {l['address']}"), cls="p-4"),
                                
                                # Pricing
                                Td(Div(format_curr(l['price_sgd']), cls="text-emerald-600 font-bold"), cls="p-4"),
                                Td(format_curr(l['price_psf']), cls="p-4 text-gray-600 font-mono text-sm"),
                                
                                # Layout
                                Td(f"{l['bedrooms']}BR / {l['bathrooms']}BA", cls="p-4 text-sm"),
                                Td(f"{l['size_sqft']}", cls="p-4 text-sm font-medium"),
                                
                                # Floor & Tenure
                                Td(l['floor_level'] or "-", cls="p-4 text-xs text-gray-500"),
                                Td(Div(l['tenure'], cls="text-[10px] leading-tight"), 
                                   Div(f"TOP: {l['top_year'] or '-'}", cls="text-xs font-bold"), cls="p-4"),
                                
                                # Agent
                                Td(Div(l['agent_name'], cls="text-xs font-bold"),
                                   Div(l['agent_phone'], cls="text-[10px] text-gray-500"), cls="p-4"),
                                
                                # Metadata
                                Td(format_date(l['scraped_at']), cls="p-4 text-[10px] text-gray-400"),
                                
                                # Action
                                Td(A("Open Listing ↗", href=l['url'], target="_blank", 
                                     cls="text-indigo-600 hover:text-indigo-900 font-bold text-xs"), cls="p-4 text-right")
                                
                            ) for l in listings]
                        )
                    )
                )
            )
        )
    )

@rt("/trigger")
def post():
    agent.start_manual_job_async()
    return Response(status_code=204)

serve()
