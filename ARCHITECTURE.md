# System Architecture: AI Real Estate Concierge (DarGlobal & Wasalt)

**Target Market:** Dubai & GCC Luxury Real Estate  
**Role Context:** Junior AI Engineer Technical Assessment & Production MVP  
**Configured Services:** OpenRouter Free Models & Qdrant Cloud Free Tier  
**Status:** Validated Architecture Specification

---

## 1. System Overview & Live Validated Stack

This system is an intelligent Real Estate Chatbot trained on publicly available property data from **DarGlobal** (luxury international developer) and **Wasalt** (leading PropTech marketplace in Saudi Arabia/GCC). 

The application uses **Qdrant Cloud** for vector similarity and metadata payload filtering, **OpenRouter free-tier LLM routing** with auto-failover, a **Dockerized** micro-architecture, and **zero-cost production cloud deployment** with a live public HTTPS URL.

```
+-----------------------------------------------------------------------------------------------+
|                                    SYSTEM OVERVIEW ARCHITECTURE                               |
|                                                                                               |
|   [DarGlobal Web / APIs]                   [Wasalt Web / APIs]                                |
|   (Luxury Branded Projects)                (Faceted Marketplace Listings)                     |
|            │                                        │                                         |
|            └───────────────────┬────────────────────┘                                         |
|                                │                                                              |
|                                ▼                                                              |
|                   [1. Ingestion & ETL Pipeline]                                               |
|             (Headless Crawl / Next.js Data Extract + Pydantic)                                |
|                                │                                                              |
|                                ▼                                                              |
|                   [2. Embedding Generation (CPU)]                                             |
|              (sentence-transformers/all-MiniLM-L6-v2, 384-dim)                                |
|                                │                                                              |
|                                ▼                                                              |
|                   [3. Qdrant Cloud Vector Database]                                           |
|              Cluster: AWS ap-northeast-2 (Free Tier)                                          |
|              - Vectors: 384-dim Cosine Distance                                               |
|              - Payloads: city, country, price_aed, bedrooms, developer, amenities             |
|              - Payload Indexes: Filterable by exact price cap, bedrooms, city                 |
|                                │                                                              |
|                                ▼                                                              |
|                   [4. Hybrid Retrieval Engine]                                                |
|              (Payload Pre-Filtering + Dense Vector Semantic Search)                           |
|                                │                                                              |
|                                ▼                                                              |
|                   [5. OpenRouter LLM Routing Engine]                                          |
|       Primary: openrouter/free (Auto-routes to best active free model)                        |
|       Fallbacks: nvidia/nemotron-3.5-lightning:free, google/gemma-4-31b-it:free,              |
|                  inclusionai/ling-3.2-flash:free                                              |
|                                │                                                              |
|                                ▼                                                              |
|                   [6. User Interface & Concierge] (Streamlit)                                 |
|              - Luxury Dubai Persona & Chat UI                                                 |
|              - Property Showcase Cards (Images, Price, Handover, Direct Links)                |
|              - Lead Capture Form (WhatsApp / Email for Private Viewing)                       |
|                                │                                                              |
|                                ▼                                                              |
|                   [7. Containerization & Free Cloud Deployment]                               |
|              (Multi-Stage Docker -> Hugging Face Spaces / Render Free Tier)                   |
|              Live Public URL: https://<username>-darglobal-ai.hf.space                        |
+-----------------------------------------------------------------------------------------------+
```

---

## 2. Infrastructure & Service Configuration

| Component | Provider / Tool | Configuration Details |
| :--- | :--- | :--- |
| **LLM Provider** | **OpenRouter (Free Tier)** | Meta-Router `openrouter/free` + Active Fallback Models |
| **Vector Database** | **Qdrant Cloud (Free Tier)** | Hosted AWS Cluster (`ap-northeast-2.aws.cloud.qdrant.io`) |
| **Embeddings** | **Sentence-Transformers** | `all-MiniLM-L6-v2` (384 dimensions, zero API cost, runs on CPU in < 25ms) |
| **Ingestion Engine** | **Playwright / JSON Extractor** | Target: DarGlobal project pages & Wasalt property search |
| **Web UI** | **Streamlit** | Branded real estate concierge with property cards and sidebar filters |
| **Container Engine** | **Docker** | Multi-stage `python:3.11-slim`, non-root user, dynamic `$PORT` |
| **Cloud Hosting** | **Hugging Face Spaces / Render** | Zero-cost public HTTPS deployment with continuous availability |

---

## 3. Detailed Component Architecture

### Component 1: Data Ingestion & Extraction (DarGlobal & Wasalt)

#### 1.1 Source Characterization
* **DarGlobal (`darglobal.co.uk`)**:
  * Focuses on luxury off-plan projects in Dubai (DG1 Living, DaVinci Tower by Pagani, W Residences Downtown, Trump Tower Dubai, D-Villas) and GCC (AIDA Oman).
  * Data points: Project Name, Location, Architectural / Brand Partner, Unit Types (1BR, 2BR, 3BR, Villas), Starting Prices (AED/USD), Handover Date, Amenities, Brochure Link.
* **Wasalt (`wasalt.sa` / `wasalt.com`)**:
  * Large PropTech marketplace with verified property listings in Riyadh, Jeddah, and GCC.
  * Data points: Listing Title, Location/District, Price, Bedrooms/Bathrooms, Area (sqft/sqm), Property Type (Apartment, Villa, Plot), Listing URL.

#### 1.2 Ingestion Best Practice
* Instead of fragile full-page HTML regex, the scraper targets:
  1. Embedded Next.js hydration payload (`<script id="__NEXT_DATA__">`).
  2. Public project catalog endpoints.
* Data is extracted into a normalized Pydantic model and saved locally to `data/processed/properties.json`.
* **Key Production Feature:** The scraped data snapshot is committed directly with the repository so that the deployed cloud container never fails due to scraping delays or remote IP restrictions.

---

### Component 2: Vector DB & Hybrid Search (Qdrant Cloud)

#### 2.1 Collection Configuration
* **Collection Name:** `darglobal_properties`
* **Vector Dimension:** 384 (matches `all-MiniLM-L6-v2`)
* **Distance Metric:** `Cosine`

#### 2.2 Payload Schema & Indexing
Qdrant Cloud allows indexing payload fields so they can be queried with instant structured filters alongside vector similarity:
* `city` (Keyword index: e.g. `"Dubai"`, `"Muscat"`, `"Riyadh"`)
* `country` (Keyword index: e.g. `"UAE"`, `"Oman"`, `"Saudi Arabia"`)
* `developer` (Keyword index: e.g. `"DarGlobal"`, `"Wasalt"`)
* `property_type` (Keyword index: e.g. `"Apartment"`, `"Villa"`, `"Penthouse"`)
* `price_aed` (Integer/Float index: allows range filtering `gte` / `lte`)
* `bedrooms` (Integer index: exact or range)
* `completion_year` (Integer index: e.g. `2026`)

#### 2.3 Hybrid Query Execution
When a user asks: *"Find me luxury 2-bedroom apartments in Dubai under 2,500,000 AED"*:
1. The parser extracts the structured filters:
   ```json
   {
     "city": "Dubai",
     "bedrooms": 2,
     "max_price": 2500000
   }
   ```
2. Qdrant executes a **single-call Hybrid Search**:
   * Evaluates the payload filter conditions (`must=[FieldCondition(key="city", match="Dubai"), FieldCondition(key="price_aed", range={"lte": 2500000})]`).
   * Scores the remaining candidate records against the semantic query vector (`"luxury canal view, high investment yield"`).
3. Returns ranked property chunks with exact numerical compliance.

---

### Component 3: LLM Orchestration with OpenRouter Free Tier

#### 3.1 Dynamic Free Model Strategy
On OpenRouter, free-tier models rotate dynamically and can experience temporary upstream throttling (HTTP 429). The system implements a **2-layer resilience pattern**:

1. **Layer 1: OpenRouter Meta-Router (`openrouter/free`)**
   * Automatically dispatches requests to the best available free model on OpenRouter (e.g. `nvidia/nemotron-3.5-lightning:free`).
2. **Layer 2: Direct Model Fallback Pool**
   * If `openrouter/free` experiences upstream latency, the client immediately catches the exception and retries across:
     - `nvidia/nemotron-3.5-lightning:free`
     - `google/gemma-4-31b-it:free`
     - `inclusionai/ling-3.2-flash:free`
     - `liquid/lfm-3-1.7b:free`
     - `particle-ai/particle-1:free`

#### 3.2 Real Estate Advisor System Prompt
The prompt enforces a **Dubai Luxury Real Estate Concierge** persona:
* Answers only with factual data present in the retrieved Qdrant payload.
* Cites exact project names, starting prices, and official project links.
* Automatically presents values in AED (and converts to USD / SAR upon request).
* Features proactive lead generation: invites the user to provide their WhatsApp or Email for a private viewing or complete PDF brochure.

---

### Component 4: Web Application (Streamlit Concierge UI)

#### 4.1 Interface Layout
* **Header:** Branded luxury real estate concierge header (DarGlobal & Wasalt co-branded aesthetic).
* **Main Chat:** Multi-turn conversational thread supporting markdown, badges, and expandable property preview cards.
* **Property Showcase Cards:**
  * Displays: High-res property image, developer badge, location, starting price in AED, handover timeline.
  * Direct CTAs: `[🔗 View Project Page]` and `[📩 Request Private Brochure]`.
* **Sidebar Controls:**
  * **Quick Filter Controls:** Dropdowns for City (Dubai, Riyadh, Muscat), Property Type (Apartment, Villa), and Budget Slider (1M – 25M AED).
  * **Lead Generation Card:** Name, WhatsApp/Phone, Email, and Preferred Move-in Date.
  * **Service Status Indicator:** Real-time badge showing Qdrant Cloud connection and OpenRouter active model.

---

### Component 5: Containerization & Cloud Deployment

#### 5.1 Dockerfile Structure
```dockerfile
# Multi-stage lightweight build
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app

# Copy installed python wheels from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application source & pre-indexed data
COPY . .

# Set non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port (dynamic for Cloud providers)
EXPOSE 7860
ENV PORT=7860

CMD ["streamlit", "run", "src/app.py", "--server.port=7860", "--server.address=0.0.0.0"]
```

#### 5.2 Zero-Cost Cloud Deployment Targets
1. **Primary: Hugging Face Spaces (Docker Runtime)**
   * Free 2 vCPU, 16GB RAM, 50GB storage.
   * Public HTTPS link: `https://huggingface.co/spaces/<user>/darglobal-concierge`
   * Direct connection to external Qdrant Cloud and OpenRouter APIs via Space Secrets.
2. **Alternative: Render.com (Web Service)**
   * Free Web Service deployed directly from GitHub.
   * Public HTTPS link: `https://darglobal-ai.onrender.com`

---

## 4. Project Directory Structure

```
DarGlobal-Wasalt-AI/
├── .env.example                    # Template for API keys
├── .gitignore                      # Standard Python & environment ignores
├── ARCHITECTURE.md                 # This system specification document
├── Dockerfile                      # Production container specification
├── README.md                       # Evaluation guide & live URL link
├── requirements.txt                # Pinned production dependencies
├── data/
│   ├── raw/
│   │   ├── darglobal_projects.json # Raw scraped DarGlobal projects
│   │   └── wasalt_listings.json    # Raw scraped Wasalt listings
│   └── processed/
│       └── properties.json         # Normalized unified dataset
└── src/
    ├── __init__.py
    ├── scraper/
    │   ├── __init__.py
    │   ├── darglobal.py            # DarGlobal extraction pipeline
    │   ├── wasalt.py               # Wasalt extraction pipeline
    │   └── normalizer.py           # Schema unification & cleaning
    ├── rag/
    │   ├── __init__.py
    │   ├── embeddings.py           # Sentence-transformers embedding wrapper
    │   ├── qdrant_manager.py       # Qdrant Cloud collection & index manager
    │   └── retriever.py            # Hybrid payload + vector search engine
    ├── llm/
    │   ├── __init__.py
    │   ├── openrouter.py           # Resilient multi-model client
    │   └── prompts.py              # Luxury real estate persona & templates
    └── app.py                      # Main Streamlit web application
```

---

## 5. Implementation Roadmap

1. **Phase 1: Ingestion Pipeline & Dataset Building**
   * Scrape and clean 25+ iconic projects & listings from DarGlobal and Wasalt.
   * Save unified JSON to `data/processed/properties.json`.
2. **Phase 2: Qdrant Cloud Collection & Indexing**
   * Generate 384-dim embeddings using `sentence-transformers/all-MiniLM-L6-v2`.
   * Create Qdrant collection `darglobal_properties` with indexed payload fields.
   * Upload all records with rich metadata.
3. **Phase 3: Resilient LLM Router**
   * Implement `openrouter/free` client with automatic fallback cycling on HTTP 429.
   * Craft the Dubai luxury real estate persona and grounded prompt template.
4. **Phase 4: Streamlit Concierge Interface**
   * Build modern web UI with property preview cards, filter sliders, and lead capture.
5. **Phase 6: Dockerization & Deployment**
   * Build and test Docker container locally.
   * Push to Hugging Face Spaces / Render and provide working live HTTPS URL.
