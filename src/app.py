"""DarGlobal & Wasalt AI Real Estate Concierge - Streamlit Application."""

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

# Page configuration
st.set_page_config(
    page_title="DarGlobal & Wasalt | AI Luxury Concierge",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Luxury Real Estate Styling
st.markdown(
    """
    <style>
    /* Dark Luxury Palette */
    .stApp {
        background-color: #0d1117;
        color: #e6edf3;
    }
    /* Brand Gold Accents */
    .gold-header {
        font-family: 'Playfair Display', Georgia, serif;
        color: #d4af37;
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0px;
    }
    .sub-header {
        color: #8b949e;
        font-size: 0.95rem;
        margin-top: -5px;
        margin-bottom: 15px;
    }
    .property-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 14px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .property-card:hover {
        border-color: #d4af37;
        transform: translateY(-2px);
    }
    .badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 6px;
    }
    .badge-darglobal {
        background-color: #3b2f11;
        color: #e5b842;
        border: 1px solid #7d601b;
    }
    .badge-wasalt {
        background-color: #172b3a;
        color: #58a6ff;
        border: 1px solid #1f6feb;
    }
    .badge-location {
        background-color: #21262d;
        color: #c9d1d9;
    }
    .price-tag {
        color: #3fb950;
        font-weight: 700;
        font-size: 1.05rem;
    }
    /* Quick prompt button style */
    div[data-testid="stButton"] > button {
        border-radius: 6px;
        border: 1px solid #30363d;
        background-color: #21262d;
        color: #e6edf3;
    }
    div[data-testid="stButton"] > button:hover {
        border-color: #d4af37;
        color: #d4af37;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner="Connecting to Real Estate AI Engine...")
def get_services():
    """Initializes and caches embedding, vector DB, and LLM services."""
    emb = EmbeddingService()
    qdrant = QdrantService()
    llm = OpenRouterClient()
    return emb, qdrant, llm


def save_lead(name: str, phone: str, email: str, notes: str) -> None:
    """Saves lead details to local data store."""
    leads_file = Path(__file__).resolve().parent.parent / "data" / "leads.json"
    leads_file.parent.mkdir(parents=True, exist_ok=True)
    existing_leads = []
    if leads_file.exists():
        try:
            with open(leads_file, encoding="utf-8") as f:
                existing_leads = json.load(f)
        except Exception:
            existing_leads = []

    lead_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "name": name,
        "phone": phone,
        "email": email,
        "notes": notes,
    }
    existing_leads.append(lead_entry)
    with open(leads_file, "w", encoding="utf-8") as f:
        json.dump(existing_leads, f, indent=2)


# Initialize services
try:
    embedder, qdrant, llm = get_services()
except Exception as e:
    st.error(f"Failed to initialize services: {e}")
    st.stop()

# Initialize session state for conversation
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Welcome to the **DarGlobal & Wasalt Real Estate Advisory**. "
                "I am your private AI concierge for prime luxury developments across Dubai, "
                "Saudi Arabia (Riyadh & Jeddah), Oman, and international capitals.\n\n"
                "How may I assist your property portfolio today?"
            ),
            "properties": [],
        }
    ]

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.markdown("<h2 style='color:#d4af37;'>Portfolio Filters</h2>", unsafe_allow_html=True)
    st.caption("Apply exact criteria to constrain search results.")

    selected_city = st.selectbox(
        "Destination / City",
        ["All", "Dubai", "Riyadh", "Muscat", "Jeddah", "Spain", "Qatar", "United Kingdom"],
        index=0,
    )

    selected_type = st.selectbox(
        "Property Type",
        ["All", "Apartments", "Villas", "Penthouse"],
        index=0,
    )

    budget_cap = st.slider(
        "Max Budget (AED)",
        min_value=1_000_000,
        max_value=30_000_000,
        value=30_000_000,
        step=500_000,
        format="%d AED",
    )
    apply_budget = st.checkbox("Enforce Budget Cap", value=False)

    st.markdown("---")
    st.markdown("<h3 style='color:#d4af37;'>Quick Advisory Queries</h3>", unsafe_allow_html=True)
    quick_prompts = [
        "Branded residences in Dubai (Pagani, Trump, W)",
        "Best investment apartments under 3M AED in Dubai",
        "Luxury 4+ bedroom villas in Riyadh",
        "Beachfront & cliffside villas in Oman AIDA",
    ]
    for qp in quick_prompts:
        if st.button(qp, key=f"btn_{qp}"):
            st.session_state.current_prompt = qp

    st.markdown("---")
    st.markdown("<h3 style='color:#d4af37;'>Request Private Viewing</h3>", unsafe_allow_html=True)
    st.caption("Connect with a private client advisor and receive official floor plans.")
    with st.form("lead_form", clear_on_submit=True):
        lead_name = st.text_input("Full Name", placeholder="e.g. Alexander Vance")
        lead_phone = st.text_input("WhatsApp / Phone", placeholder="+971 50 123 4567")
        lead_email = st.text_input("Email", placeholder="investor@domain.com")
        lead_notes = st.text_area("Preferences / Inquiries", placeholder="Interested in 2BR canal view in Business Bay...")
        submitted = st.form_submit_button("Submit Request")
        if submitted:
            if lead_name and (lead_phone or lead_email):
                save_lead(lead_name, lead_phone, lead_email, lead_notes)
                st.success("Your request has been received. A senior advisor will contact you shortly.")
            else:
                st.warning("Please provide your name and at least a phone number or email.")

# ----------------- MAIN VIEW -----------------
st.markdown("<div class='gold-header'>DARGLOBAL & WASALT</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='sub-header'>AI Luxury Concierge | Dubai &bull; Riyadh &bull; Muscat &bull; Marbella &bull; London</div>",
    unsafe_allow_html=True,
)

# Render Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("properties"):
            st.markdown("---")
            st.caption("✨ **Featured Matches from Catalog:**")
            cols = st.columns(min(len(msg["properties"]), 3))
            for i, prop in enumerate(msg["properties"][:3]):
                with cols[i]:
                    badge_class = "badge-darglobal" if prop.get("source") == "DarGlobal" else "badge-wasalt"
                    st.markdown(
                        f"""
                        <div class='property-card'>
                            <span class='badge {badge_class}'>{prop.get('source')}</span>
                            <span class='badge badge-location'>{prop.get('city')}</span>
                            <h4 style='color:#e6edf3; margin-top:8px; margin-bottom:4px;'>{prop.get('title')}</h4>
                            <p class='price-tag'>{prop.get('price_aed', 0):,.0f} AED</p>
                            <p style='color:#8b949e; font-size:0.85rem; margin-bottom:8px;'>
                                <b>Handover:</b> {prop.get('completion_date', 'Ready')}<br/>
                                <b>Type:</b> {prop.get('property_type', 'Residence')}
                            </p>
                            <a href='{prop.get('source_url')}' target='_blank' style='color:#d4af37; font-weight:600; text-decoration:none;'>🔗 View Project Page &rarr;</a>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

# Handle Input
prompt_input = st.chat_input("Ask about developments, pricing, payment plans, or locations...")
active_query = getattr(st.session_state, "current_prompt", None) or prompt_input

if active_query:
    st.session_state.current_prompt = None

    # Render User Message
    st.session_state.messages.append({"role": "user", "content": active_query})
    with st.chat_message("user"):
        st.markdown(active_query)

    # Retrieval
    with st.spinner("Analyzing portfolio & matching properties..."):
        query_vec = embedder.embed_text(active_query)
        max_p = budget_cap if apply_budget else None
        c_filter = selected_city if selected_city != "All" else None
        t_filter = selected_type if selected_type != "All" else None

        matched_props = qdrant.search(
            query_vector=query_vec,
            city=c_filter,
            max_price_aed=max_p,
            property_type=t_filter,
            limit=4,
        )

    # LLM Stream Response
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""

        # Build conversation history for context
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[-4:]
            if m["role"] in ["user", "assistant"]
        ]

        stream_gen = llm.stream_response(
            query=active_query,
            context_properties=matched_props,
            conversation_history=history,
        )

        for chunk in stream_gen:
            full_response += chunk
            response_placeholder.markdown(full_response + "▌")

        response_placeholder.markdown(full_response)

        # Show Property Cards below the generated response
        if matched_props:
            st.markdown("---")
            st.caption("✨ **Featured Matches from Catalog:**")
            cols = st.columns(min(len(matched_props), 3))
            for i, prop in enumerate(matched_props[:3]):
                with cols[i]:
                    badge_class = "badge-darglobal" if prop.get("source") == "DarGlobal" else "badge-wasalt"
                    st.markdown(
                        f"""
                        <div class='property-card'>
                            <span class='badge {badge_class}'>{prop.get('source')}</span>
                            <span class='badge badge-location'>{prop.get('city')}</span>
                            <h4 style='color:#e6edf3; margin-top:8px; margin-bottom:4px;'>{prop.get('title')}</h4>
                            <p class='price-tag'>{prop.get('price_aed', 0):,.0f} AED</p>
                            <p style='color:#8b949e; font-size:0.85rem; margin-bottom:8px;'>
                                <b>Handover:</b> {prop.get('completion_date', 'Ready')}<br/>
                                <b>Type:</b> {prop.get('property_type', 'Residence')}
                            </p>
                            <a href='{prop.get('source_url')}' target='_blank' style='color:#d4af37; font-weight:600; text-decoration:none;'>🔗 View Project Page &rarr;</a>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    # Store assistant message
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": full_response,
            "properties": matched_props,
        }
    )
