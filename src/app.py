"""DarGlobal & Wasalt AI Real Estate Concierge - Luxury Web Application."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

from src.rag.embeddings import EmbeddingService
from src.rag.qdrant_service import QdrantService
from src.llm.client import OpenRouterClient

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Currency conversion rates (Base: AED)
EXCHANGE_RATES = {
    "AED": 1.0,
    "SAR": 1.02,     # 1 AED ~ 1.02 SAR
    "USD": 0.272,    # 1 AED ~ 0.272 USD
    "EUR": 0.252,    # 1 AED ~ 0.252 EUR
    "GBP": 0.215,    # 1 AED ~ 0.215 GBP
}
CURRENCY_SYMBOLS = {
    "AED": "AED",
    "SAR": "SAR",
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
}

# Streamlit Page Config
st.set_page_config(
    page_title="DarGlobal & Wasalt | Luxury Real Estate Concierge",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Bespoke Luxury Real Estate CSS & Glassmorphism Theme
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@500;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,600;0,700;1,400&display=swap');

    /* Global Background & Typography */
    .stApp {
        background: radial-gradient(circle at 20% 10%, #0d131f 0%, #070a0f 100%);
        color: #e6edf3;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* Gold Metallic Gradients */
    .gold-text {
        font-family: 'Cinzel', serif;
        background: linear-gradient(135deg, #f6e27a 0%, #d4af37 50%, #aa771c 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: 1.5px;
    }
    .gold-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, #d4af37, transparent);
        margin: 20px 0;
    }

    /* Top Brand Navigation Bar */
    .brand-hero {
        background: rgba(18, 24, 38, 0.7);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(212, 175, 55, 0.25);
        border-radius: 12px;
        padding: 24px 32px;
        margin-bottom: 24px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    }
    .hero-title {
        font-family: 'Cinzel', serif;
        font-size: 2.1rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: 2px;
    }
    .hero-subtitle {
        font-family: 'Playfair Display', serif;
        color: #8b9bb4;
        font-size: 1.05rem;
        margin-top: 6px;
        letter-spacing: 0.5px;
    }
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.35);
        color: #34d399;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 4px 12px;
        border-radius: 20px;
        margin-right: 8px;
    }
    .status-dot {
        width: 7px;
        height: 7px;
        background-color: #10b981;
        border-radius: 50%;
        box-shadow: 0 0 8px #10b981;
    }

    /* Luxury Property Card */
    .property-card-container {
        background: rgba(15, 21, 33, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        overflow: hidden;
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        margin-bottom: 18px;
        display: flex;
        flex-direction: column;
        height: 100%;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }
    .property-card-container:hover {
        border-color: #d4af37;
        transform: translateY(-4px);
        box-shadow: 0 12px 32px rgba(212, 175, 55, 0.15);
    }
    .card-img-wrapper {
        position: relative;
        width: 100%;
        height: 180px;
        overflow: hidden;
        background-color: #1a2233;
    }
    .card-img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        transition: transform 0.5s ease;
    }
    .property-card-container:hover .card-img {
        transform: scale(1.05);
    }
    .card-content {
        padding: 16px 18px;
        flex-grow: 1;
        display: flex;
        flex-direction: column;
    }
    .badge-tag {
        display: inline-block;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        padding: 3px 8px;
        border-radius: 4px;
        margin-bottom: 8px;
        margin-right: 5px;
    }
    .badge-dg {
        background: linear-gradient(135deg, rgba(212, 175, 55, 0.2), rgba(212, 175, 55, 0.05));
        border: 1px solid #d4af37;
        color: #f6e27a;
    }
    .badge-ws {
        background: linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(56, 189, 248, 0.05));
        border: 1px solid #38bdf8;
        color: #7dd3fc;
    }
    .card-title {
        font-family: 'Cinzel', serif;
        font-size: 1.05rem;
        font-weight: 700;
        color: #ffffff;
        margin: 4px 0 8px 0;
        line-height: 1.3;
    }
    .card-price {
        font-family: 'Cinzel', serif;
        font-size: 1.15rem;
        font-weight: 700;
        color: #f6e27a;
        margin-bottom: 8px;
    }
    .card-specs {
        color: #94a3b8;
        font-size: 0.82rem;
        line-height: 1.5;
        margin-bottom: 12px;
    }
    .card-specs b {
        color: #cbd5e1;
    }
    .card-btn {
        margin-top: auto;
        display: inline-block;
        text-align: center;
        background: rgba(212, 175, 55, 0.12);
        border: 1px solid rgba(212, 175, 55, 0.4);
        color: #f6e27a !important;
        padding: 8px 14px;
        border-radius: 6px;
        text-decoration: none !important;
        font-size: 0.82rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        transition: all 0.2s ease;
    }
    .card-btn:hover {
        background: #d4af37;
        color: #070a0f !important;
        border-color: #d4af37;
    }

    /* Metric Cards in Analytics */
    .metric-card {
        background: rgba(18, 24, 38, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 18px;
        text-align: center;
    }
    .metric-val {
        font-family: 'Cinzel', serif;
        font-size: 1.8rem;
        font-weight: 700;
        color: #f6e27a;
    }
    .metric-label {
        color: #94a3b8;
        font-size: 0.85rem;
        margin-top: 4px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #080c14;
        border-right: 1px solid rgba(212, 175, 55, 0.2);
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        padding-bottom: 8px;
        margin-bottom: 16px;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-weight: 600;
        color: #94a3b8;
        border-radius: 8px;
        padding: 8px 18px;
        background: transparent;
        border: 1px solid transparent;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(212, 175, 55, 0.15) !important;
        border: 1px solid #d4af37 !important;
        color: #f6e27a !important;
    }

    /* Custom Input & Chat Styling */
    .stChatInputContainer {
        border-color: rgba(212, 175, 55, 0.4) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner="Initializing Real Estate Intelligence System...")
def load_core_services():
    """Initializes and caches embedding, Qdrant Cloud, and LLM services."""
    emb = EmbeddingService()
    qdrant = QdrantService()
    llm = OpenRouterClient()
    return emb, qdrant, llm


@st.cache_data
def load_all_properties():
    """Loads all 76 normalized property records for visual browsing."""
    data_file = Path(__file__).resolve().parent.parent / "data" / "processed" / "properties.json"
    if data_file.exists():
        with open(data_file, encoding="utf-8") as f:
            return json.load(f)
    return []


def format_price(price_aed: float, currency: str) -> str:
    """Formats AED price into selected currency with localized formatting."""
    if not price_aed:
        return "Price on Application"
    rate = EXCHANGE_RATES.get(currency, 1.0)
    sym = CURRENCY_SYMBOLS.get(currency, currency)
    converted = price_aed * rate
    if currency in ["USD", "EUR", "GBP"]:
        return f"{sym}{converted:,.0f}"
    return f"{converted:,.0f} {sym}"


def save_lead(name: str, phone: str, email: str, notes: str, preferred_property: str = "General Inquiry") -> None:
    """Persists private client leads."""
    leads_file = Path(__file__).resolve().parent.parent / "data" / "leads.json"
    leads_file.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if leads_file.exists():
        try:
            with open(leads_file, encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []

    lead_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "name": name,
        "phone": phone,
        "email": email,
        "property_interest": preferred_property,
        "notes": notes,
    }
    existing.append(lead_entry)
    with open(leads_file, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)


# Load services & dataset
try:
    embedder, qdrant, llm = load_core_services()
    all_properties = load_all_properties()
except Exception as e:
    st.error(f"Error initializing system services: {e}")
    st.stop()

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.markdown("<h2 class='gold-text' style='font-size:1.4rem; margin-bottom:4px;'>PORTFOLIO SUITE</h2>", unsafe_allow_html=True)
    st.caption("Custom Private Wealth Advisory Filters")

    # Currency Switcher
    selected_currency = st.selectbox(
        "💱 Presentation Currency",
        options=["AED", "SAR", "USD", "EUR", "GBP"],
        index=0,
        help="Converts all listing prices and budget filters live.",
    )

    st.markdown("<div class='gold-divider'></div>", unsafe_allow_html=True)
    st.markdown("<h4 style='color:#f6e27a; font-size:0.95rem; margin-bottom:8px;'>PORTFOLIO FILTERS</h4>", unsafe_allow_html=True)

    city_options = ["All Destinations", "Dubai", "Riyadh", "Muscat", "Jeddah", "Spain", "Qatar", "United Kingdom"]
    selected_city = st.selectbox("Destination / Region", city_options, index=0)

    type_options = ["All Types", "Apartments", "Villas", "Penthouse"]
    selected_type = st.selectbox("Property Class", type_options, index=0)

    # Budget cap calculation in chosen currency
    rate = EXCHANGE_RATES.get(selected_currency, 1.0)
    max_budget_native = 35_000_000 * rate
    step_native = max(50_000, int(500_000 * rate))
    budget_slider = st.slider(
        f"Maximum Budget ({selected_currency})",
        min_value=int(1_000_000 * rate),
        max_value=int(max_budget_native),
        value=int(max_budget_native),
        step=step_native,
    )
    apply_budget = st.checkbox("Enforce Strict Budget Cap", value=False)
    budget_cap_aed = (budget_slider / rate) if apply_budget else None

    st.markdown("<div class='gold-divider'></div>", unsafe_allow_html=True)
    st.markdown("<h4 style='color:#f6e27a; font-size:0.95rem; margin-bottom:8px;'>EXECUTIVE INQUIRIES</h4>", unsafe_allow_html=True)
    quick_queries = [
        "Branded residences in Dubai (Pagani, Trump, W)",
        "Best investment apartments under 2.5M AED in Dubai",
        "Luxury 4+ bedroom villas in Riyadh",
        "Cliffside & golf villas at AIDA Oman",
        "Tierra Viva Lamborghini villas in Marbella",
    ]
    for q in quick_queries:
        if st.button(q, key=f"btn_{q}"):
            st.session_state.active_query = q

    st.markdown("<div class='gold-divider'></div>", unsafe_allow_html=True)
    st.markdown("<h4 style='color:#f6e27a; font-size:0.95rem; margin-bottom:4px;'>PRIVATE BROCHURE REQUEST</h4>", unsafe_allow_html=True)
    st.caption("Receive confidential floor plans & developer payment terms.")
    with st.form("vip_lead_form", clear_on_submit=True):
        lead_name = st.text_input("Full Name", placeholder="e.g. H.E. Tariq Al-Mansoor")
        lead_phone = st.text_input("WhatsApp / Mobile", placeholder="+971 50 000 0000")
        lead_email = st.text_input("Confidential Email", placeholder="tariq@familyoffice.com")
        lead_notes = st.text_area("Acquisition Notes", placeholder="Looking for 2-3 BR canal view, payment plan...")
        submitted = st.form_submit_button("Submit Acquisition Brief")
        if submitted:
            if lead_name and (lead_phone or lead_email):
                save_lead(lead_name, lead_phone, lead_email, lead_notes)
                st.success("Brief registered. A Senior Relationship Manager will connect shortly.")
            else:
                st.warning("Please provide your name and at least a contact method.")

    st.markdown("<div class='gold-divider'></div>", unsafe_allow_html=True)
    # Telemetry Status
    st.markdown(
        f"""
        <div style='background:rgba(255,255,255,0.03); border-radius:8px; padding:10px; font-size:0.75rem; color:#64748b;'>
            <b>System Telemetry</b><br/>
            • <b>Vector DB:</b> Qdrant Cloud (AWS ap-ne-2)<br/>
            • <b>Catalog:</b> {len(all_properties)} Prime Assets<br/>
            • <b>LLM:</b> OpenRouter Free Tier (Dynamic Router)<br/>
            • <b>Embeddings:</b> 384-dim Dense (CPU Fast)
        </div>
        """,
        unsafe_allow_html=True,
    )

# ----------------- MAIN VIEW -----------------
# Hero Banner
st.markdown(
    """
    <div class='brand-hero'>
        <div style='display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap;'>
            <div>
                <h1 class='hero-title gold-text'>DARGLOBAL & WASALT</h1>
                <div class='hero-subtitle'>Private Wealth & Ultra-Luxury Real Estate Advisory</div>
                <div style='color:#64748b; font-size:0.85rem; margin-top:4px;'>
                    Dubai &bull; Riyadh &bull; Muscat &bull; Marbella &bull; London &bull; Doha
                </div>
            </div>
            <div style='display:flex; gap:8px; margin-top:8px;'>
                <span class='status-pill'><span class='status-dot'></span> Qdrant Cloud Live</span>
                <span class='status-pill'><span class='status-dot'></span> OpenRouter Free Active</span>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Navigation Tabs
tab_chat, tab_catalog, tab_analytics = st.tabs(
    ["💬 AI Private Concierge", "🏛️ Property Portfolio Explorer", "📊 Market Analytics & Intelligence"]
)

# ================= TAB 1: AI CONCIERGE CHAT =================
with tab_chat:
    col_chat_main, col_chat_side = st.columns([7, 3])

    with col_chat_main:
        if "messages" not in st.session_state:
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": (
                        "Welcome to the **DarGlobal & Wasalt Real Estate Advisory**. "
                        "I am your private AI concierge specializing in landmark branded developments and verified prime properties across "
                        "**Dubai**, **Saudi Arabia** (Riyadh & Jeddah), **Oman**, and international capitals.\n\n"
                        "How may I assist your acquisition strategy or property search today?"
                    ),
                    "properties": [],
                }
            ]

        # Display Chat History
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

                # Render embedded property cards if attached
                props = msg.get("properties", [])
                if props:
                    st.markdown("<div style='margin-top:12px; margin-bottom:8px; font-size:0.85rem; color:#d4af37; font-weight:600;'>✨ MATCHING PORTFOLIO ASSETS:</div>", unsafe_allow_html=True)
                    cols = st.columns(min(len(props), 3))
                    for i, p in enumerate(props[:3]):
                        with cols[i]:
                            badge_cls = "badge-dg" if p.get("source") == "DarGlobal" else "badge-ws"
                            formatted_p = format_price(p.get("price_aed", 0), selected_currency)
                            img_src = p.get("image_url") or "https://cdn.darglobal.co.uk/large_TTD_exterior_02_bd7d425e3c.webp"
                            st.markdown(
                                f"""
                                <div class='property-card-container'>
                                    <div class='card-img-wrapper'>
                                        <img src='{img_src}' class='card-img' onerror="this.src='https://cdn.darglobal.co.uk/large_TTD_exterior_02_bd7d425e3c.webp';"/>
                                    </div>
                                    <div class='card-content'>
                                        <div>
                                            <span class='badge-tag {badge_cls}'>{p.get('source')}</span>
                                            <span class='badge-tag' style='background:rgba(255,255,255,0.06); color:#cbd5e1;'>{p.get('city')}</span>
                                        </div>
                                        <div class='card-title'>{p.get('title')}</div>
                                        <div class='card-price'>{formatted_p}</div>
                                        <div class='card-specs'>
                                            <b>Handover:</b> {p.get('completion_date', 'Ready')}<br/>
                                            <b>Type:</b> {p.get('property_type', 'Residence')}
                                        </div>
                                        <a href='{p.get('source_url')}' target='_blank' class='card-btn'>View Project Page &rarr;</a>
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

        # Handle Chat Input
        user_input = st.chat_input("Inquire about projects, pricing, branded residences, or locations...")
        current_query = getattr(st.session_state, "active_query", None) or user_input

        if current_query:
            st.session_state.active_query = None

            # Render user query
            st.session_state.messages.append({"role": "user", "content": current_query})
            with st.chat_message("user"):
                st.markdown(current_query)

            # RAG Retrieval
            with st.spinner("Analyzing portfolio with Qdrant Hybrid Search..."):
                query_vector = embedder.embed_text(current_query)
                city_filter = selected_city if selected_city != "All Destinations" else None
                type_filter = selected_type if selected_type != "All Types" else None

                matched_records = qdrant.search(
                    query_vector=query_vector,
                    city=city_filter,
                    max_price_aed=budget_cap_aed,
                    property_type=type_filter,
                    limit=3,
                )

            # Stream LLM Response
            with st.chat_message("assistant"):
                placeholder = st.empty()
                accumulated = ""

                history = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages[-4:]
                    if m["role"] in ["user", "assistant"]
                ]

                stream = llm.stream_response(
                    query=current_query,
                    context_properties=matched_records,
                    conversation_history=history,
                )

                for chunk in stream:
                    accumulated += chunk
                    placeholder.markdown(accumulated + "▌")

                placeholder.markdown(accumulated)

                # Show property cards
                if matched_records:
                    st.markdown("<div style='margin-top:12px; margin-bottom:8px; font-size:0.85rem; color:#d4af37; font-weight:600;'>✨ MATCHING PORTFOLIO ASSETS:</div>", unsafe_allow_html=True)
                    cols = st.columns(min(len(matched_records), 3))
                    for i, p in enumerate(matched_records[:3]):
                        with cols[i]:
                            badge_cls = "badge-dg" if p.get("source") == "DarGlobal" else "badge-ws"
                            formatted_p = format_price(p.get("price_aed", 0), selected_currency)
                            img_src = p.get("image_url") or "https://cdn.darglobal.co.uk/large_TTD_exterior_02_bd7d425e3c.webp"
                            st.markdown(
                                f"""
                                <div class='property-card-container'>
                                    <div class='card-img-wrapper'>
                                        <img src='{img_src}' class='card-img' onerror="this.src='https://cdn.darglobal.co.uk/large_TTD_exterior_02_bd7d425e3c.webp';"/>
                                    </div>
                                    <div class='card-content'>
                                        <div>
                                            <span class='badge-tag {badge_cls}'>{p.get('source')}</span>
                                            <span class='badge-tag' style='background:rgba(255,255,255,0.06); color:#cbd5e1;'>{p.get('city')}</span>
                                        </div>
                                        <div class='card-title'>{p.get('title')}</div>
                                        <div class='card-price'>{formatted_p}</div>
                                        <div class='card-specs'>
                                            <b>Handover:</b> {p.get('completion_date', 'Ready')}<br/>
                                            <b>Type:</b> {p.get('property_type', 'Residence')}
                                        </div>
                                        <a href='{p.get('source_url')}' target='_blank' class='card-btn'>View Project Page &rarr;</a>
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": accumulated,
                    "properties": matched_records,
                }
            )

    with col_chat_side:
        st.markdown(
            """
            <div style='background:rgba(18,24,38,0.7); border:1px solid rgba(255,255,255,0.08); border-radius:10px; padding:18px;'>
                <h4 class='gold-text' style='font-size:1.05rem; margin-bottom:6px;'>ADVISORY GUIDELINES</h4>
                <p style='color:#94a3b8; font-size:0.83rem; line-height:1.6;'>
                    Our concierge assists with acquisitions across high-growth GCC corridors and branded international residences.
                </p>
                <div class='gold-divider' style='margin:12px 0;'></div>
                <h5 style='color:#cbd5e1; font-size:0.85rem; margin-bottom:8px;'>Branded Collaborations</h5>
                <ul style='color:#94a3b8; font-size:0.8rem; padding-left:18px; line-height:1.6;'>
                    <li><b>Pagani:</b> DaVinci Tower & Penthouse</li>
                    <li><b>Aston Martin:</b> The Astera (RAK)</li>
                    <li><b>Lamborghini:</b> Tierra Viva (Spain)</li>
                    <li><b>W Hotels:</b> W Residences Downtown</li>
                    <li><b>Trump:</b> Dubai, Jeddah, AIDA Oman</li>
                    <li><b>Missoni:</b> Urban Oasis & Marea</li>
                </ul>
                <div class='gold-divider' style='margin:12px 0;'></div>
                <h5 style='color:#cbd5e1; font-size:0.85rem; margin-bottom:6px;'>Investor Services</h5>
                <p style='color:#94a3b8; font-size:0.8rem; line-height:1.5;'>
                    Inquire about 60/40 payment schedules, rental yield estimates in Business Bay, or Saudi REGA-verified title deed acquisitions.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ================= TAB 2: PORTFOLIO EXPLORER =================
with tab_catalog:
    st.markdown("<h3 class='gold-text' style='font-size:1.4rem; margin-bottom:4px;'>CURATED ASSET CATALOG</h3>", unsafe_allow_html=True)
    st.caption(f"Explore all {len(all_properties)} verified properties and developments across the GCC and Europe.")

    # Explorer Filter Bar
    f_col1, f_col2, f_col3 = st.columns([4, 3, 3])
    with f_col1:
        search_kw = st.text_input("🔍 Search by Project, Brand, or Location", placeholder="e.g. Pagani, Business Bay, Golf...")
    with f_col2:
        cat_city = st.selectbox("Filter by Destination", ["All"] + sorted(list({p["city"] for p in all_properties})), key="cat_city")
    with f_col3:
        cat_dev = st.selectbox("Developer / Partner", ["All", "DarGlobal", "Wasalt"], key="cat_dev")

    # Filter logic
    filtered = all_properties
    if search_kw:
        kw = search_kw.lower()
        filtered = [p for p in filtered if kw in p["title"].lower() or kw in p["description"].lower() or kw in (p.get("brand_partner") or "").lower()]
    if cat_city != "All":
        filtered = [p for p in filtered if p["city"] == cat_city]
    if cat_dev != "All":
        filtered = [p for p in filtered if p["source"] == cat_dev]

    st.markdown(f"<div style='color:#94a3b8; font-size:0.85rem; margin-bottom:14px;'>Displaying <b>{len(filtered)}</b> matching properties:</div>", unsafe_allow_html=True)

    # 3-column Grid
    grid_cols = st.columns(3)
    for idx, prop in enumerate(filtered):
        col_idx = idx % 3
        with grid_cols[col_idx]:
            badge_cls = "badge-dg" if prop.get("source") == "DarGlobal" else "badge-ws"
            formatted_p = format_price(prop.get("price_aed", 0), selected_currency)
            img_src = prop.get("image_url") or "https://cdn.darglobal.co.uk/large_TTD_exterior_02_bd7d425e3c.webp"
            brand_pill = f"<span class='badge-tag' style='background:rgba(212,175,55,0.15); border:1px solid #d4af37; color:#f6e27a;'>✨ {prop.get('brand_partner')}</span>" if prop.get("brand_partner") else ""

            st.markdown(
                f"""
                <div class='property-card-container'>
                    <div class='card-img-wrapper'>
                        <img src='{img_src}' class='card-img' onerror="this.src='https://cdn.darglobal.co.uk/large_TTD_exterior_02_bd7d425e3c.webp';"/>
                    </div>
                    <div class='card-content'>
                        <div>
                            <span class='badge-tag {badge_cls}'>{prop.get('source')}</span>
                            <span class='badge-tag' style='background:rgba(255,255,255,0.06); color:#cbd5e1;'>{prop.get('city')}</span>
                            {brand_pill}
                        </div>
                        <div class='card-title'>{prop.get('title')}</div>
                        <div class='card-price'>{formatted_p}</div>
                        <div class='card-specs'>
                            <b>Handover:</b> {prop.get('completion_date', 'Ready')}<br/>
                            <b>Type:</b> {prop.get('property_type', 'Residence')} &bull; <b>Beds:</b> {prop.get('bedrooms', 'Inquire')}
                        </div>
                        <a href='{prop.get('source_url')}' target='_blank' class='card-btn'>View Project Page &rarr;</a>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# ================= TAB 3: MARKET ANALYTICS =================
with tab_analytics:
    st.markdown("<h3 class='gold-text' style='font-size:1.4rem; margin-bottom:4px;'>PORTFOLIO INTELLIGENCE & METRICS</h3>", unsafe_allow_html=True)
    st.caption("Key portfolio distribution, valuation benchmarks, and brand partnerships.")

    # High-level Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(
            f"""
            <div class='metric-card'>
                <div class='metric-val'>{len(all_properties)}</div>
                <div class='metric-label'>Total Properties</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m2:
        dg_count = sum(1 for p in all_properties if p["source"] == "DarGlobal")
        st.markdown(
            f"""
            <div class='metric-card'>
                <div class='metric-val'>{dg_count}</div>
                <div class='metric-label'>DarGlobal Flagships</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m3:
        ws_count = sum(1 for p in all_properties if p["source"] == "Wasalt")
        st.markdown(
            f"""
            <div class='metric-card'>
                <div class='metric-val'>{ws_count}</div>
                <div class='metric-label'>Wasalt Verified Units</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m4:
        avg_aed = sum(p.get("price_aed", 0) for p in all_properties if p.get("price_aed")) / max(1, len(all_properties))
        formatted_avg = format_price(avg_aed, selected_currency)
        st.markdown(
            f"""
            <div class='metric-card'>
                <div class='metric-val'>{formatted_avg}</div>
                <div class='metric-label'>Portfolio Avg Valuation</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div class='gold-divider'></div>", unsafe_allow_html=True)

    # City Distribution Breakdown
    c_left, c_right = st.columns(2)
    with c_left:
        st.markdown("<h4 style='color:#f6e27a; font-size:1.05rem;'>Regional Geographic Footprint</h4>", unsafe_allow_html=True)
        city_counts = {}
        for p in all_properties:
            city_counts[p["city"]] = city_counts.get(p["city"], 0) + 1

        for c, count in sorted(city_counts.items(), key=lambda x: x[1], reverse=True):
            pct = (count / len(all_properties)) * 100
            st.markdown(f"**{c}** ({count} properties — {pct:.1f}%)")
            st.progress(pct / 100)

    with c_right:
        st.markdown("<h4 style='color:#f6e27a; font-size:1.05rem;'>Branded Residences & Co-Design Portfolio</h4>", unsafe_allow_html=True)
        st.markdown(
            """
            DarGlobal collaborates with the world’s most renowned luxury, hospitality, and automotive houses:
            * **Automobili Lamborghini:** *Tierra Viva (Benahavis, Spain)* — Ultra-luxury private villas inspired by supercar dynamics.
            * **Pagani Automobili:** *DaVinci Tower & The Pagani Penthouse (Dubai Canal)* — Carbon-fiber accents, bespoke Italian craft.
            * **Aston Martin:** *The Astera (Al Marjan Island, RAK)* — Coastal residences near the upcoming Wynn Resort.
            * **W Hotels Worldwide:** *W Residences Downtown Dubai* — Unrivaled Burj Khalifa panoramas with 24/7 dedicated concierge.
            * **The Trump Organization:** *Trump Tower Dubai, Trump Mansions (Wadi Safar), Trump Tower Jeddah, AIDA (Oman)*.
            * **Missoni:** *Urban Oasis (Business Bay) & Marea (Finca Cortesin, Spain)* — Vibrant Mediterranean haute couture design.
            * **Gensler Architects:** *DG1 Living (Dubai)* — Striking kinetic architecture along the Dubai Water Canal.
            """
        )
