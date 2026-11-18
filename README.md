# DarGlobal & Wasalt AI Luxury Real Estate Concierge

> **Production MVP & Technical Assessment for Junior AI Engineer (Dubai / GCC Market)**  
> **Author:** AI Engineering Candidate  
> **Tech Stack:** Python 3.11 | Qdrant Cloud (Hosted) | OpenRouter Free Tier | Sentence-Transformers | Streamlit | Docker

---

## 1. Project Overview

This application is an enterprise-grade AI Real Estate Concierge trained on publicly available property and development data from **DarGlobal** (leading international luxury developer) and **Wasalt** (premier Saudi Arabian & GCC PropTech marketplace).

### Core Capabilities
* **Grounded Luxury Advisory:** Accurately advises clients on flagship developments (DG1 Living, DaVinci Tower by Pagani, W Residences Downtown Dubai, Trump International Hotel & Tower Dubai, D-Villas Jumeirah Golf Estates, AIDA Oman, etc.) and verified listings in Riyadh/Jeddah.
* **Hybrid Retrieval (Vector Search + Exact Payload Filtering):** Solves the classic RAG limitation where pure vector search hallucinates numbers by enforcing hard constraints on budget, bedroom count, and city directly in **Qdrant Cloud**.
* **Zero-Cost OpenRouter Free Model Routing:** Automatically dispatches queries through `openrouter/free` and cascades through a resilient fallback pool (`nvidia/nemotron-3.5-lightning:free`, `inclusionai/ling-3.2-flash:free`, etc.) to withstand upstream provider rate limits (HTTP 429).
* **Enterprise UX & Lead Capture:** Interactive property preview cards with direct links to official developer project pages and an integrated private viewing / brochure request lead-capture pipeline.
* **100% Dockerized & Free Cloud Ready:** Configured for zero-cost deployment on Hugging Face Spaces or Render with persistent public HTTPS access.

---

## 2. Architecture & Data Flow

```
+───────────────────────────────────────────────────────────────────────────────────+
|                           DATA EXTRACTION & ETL PIPELINE                          |
|  [DarGlobal Projects (38 Developments)]        [Wasalt Listings (38 Properties)]  |
|                 │                                              │                  |
|                 └───────────────────────┬──────────────────────┘                  |
|                                         ▼                                         |
|                           [Unified Property Schema]                               |
|                     (Pydantic validation, SAR->AED FX)                            |
+─────────────────────────────────────────┬─────────────────────────────────────────+
                                          ▼
+───────────────────────────────────────────────────────────────────────────────────+
|                       QDRANT CLOUD HYBRID RETRIEVAL ENGINE                        |
|                                                                                   |
|   User Query ──► [Fast Embeddings: sentence-transformers/all-MiniLM-L6-v2]        |
|                                         │ (384-dim Dense Vector)                  |
|                                         ▼                                         |
|                  [Qdrant Cloud Cluster (AWS ap-northeast-2)]                      |
|                  - Cosine Distance Vector Similarity                              |
|                  - Payload Pre-Filter: (city, max_price_aed, bedrooms, type)      |
+─────────────────────────────────────────┬─────────────────────────────────────────+
                                          ▼
+───────────────────────────────────────────────────────────────────────────────────+
|                        RESILIENT OPENROUTER LLM ROUTER                            |
|             Primary: openrouter/free (Auto-routes to active free tier)             |
|                                         │ (on HTTP 429 / failover)                |
|                                         ▼                                         |
|             Fallback: nvidia/nemotron ──► ling-3.2-flash ──► liquid/lfm-3         |
+─────────────────────────────────────────┬─────────────────────────────────────────+
                                          ▼
+───────────────────────────────────────────────────────────────────────────────────+
|                             STREAMLIT CONCIERGE UI                                |
|  - Real Estate Concierge Chat with live token streaming                           |
|  - Property Cards (Hero Image, Starting Price, Handover Year, Direct Link)        |
|  - Portfolio Filters (City, Budget Slider, Property Type)                         |
|  - Lead Capture Form (WhatsApp / Email for Private Client Team)                   |
+───────────────────────────────────────────────────────────────────────────────────+
```

---

## 3. Live Deployment Guide (Free Public URL)

To satisfy the requirement of providing a **live working URL without incurring hosting costs**, deploy via **Hugging Face Spaces** (recommended) or **Render.com**.

### Option A: Deploy to Hugging Face Spaces (Recommended - 100% Free)
Hugging Face Spaces provides a **free Docker environment** with 2 vCPUs, 16GB RAM, persistent HTTPS URL, and zero credit card required:

1. Create a free account at [huggingface.co](https://huggingface.co).
2. Click **New Space** &rarr; Name: `darglobal-concierge`.
3. Select **Space SDK:** `Docker` &rarr; Choose **Blank** template.
4. Clone your space repository or upload the files from this repository:
   ```bash
   git remote add space https://huggingface.co/spaces/<your-username>/darglobal-concierge
   git push space master
   ```
5. In your Space **Settings &rarr; Variables and secrets**, add two secrets:
   * `OPENROUTER_API_KEY` = `<your_openrouter_api_key>`
   * `QDRANT_API_KEY` = `<your_qdrant_api_key>`
   * `QDRANT_URL` = `https://072171e4-90fb-49cd-849d-0a1afde67e8d.ap-northeast-2-0.aws.cloud.qdrant.io`
6. Your Space will build and launch at:
   `https://huggingface.co/spaces/<your-username>/darglobal-concierge`

### Option B: Deploy to Render.com (Web Service - Free)
1. Push this repository to GitHub.
2. In [Render Dashboard](https://dashboard.render.com), click **New &rarr; Web Service**.
3. Connect your GitHub repository and select **Docker** runtime.
4. Add environment variables:
   * `OPENROUTER_API_KEY`
   * `QDRANT_API_KEY`
   * `QDRANT_URL` = `https://072171e4-90fb-49cd-849d-0a1afde67e8d.ap-northeast-2-0.aws.cloud.qdrant.io`
   * `QDRANT_COLLECTION` = `darglobal_properties`
5. Click **Deploy Web Service** &rarr; Provides instant live URL: `https://darglobal-bot.onrender.com`.

---

## 4. Local Execution & Docker Instructions

### Method 1: Run with Docker Compose (Recommended)
Ensure Docker Desktop is running, then execute:
```bash
docker compose up --build
```
Open your browser at `http://localhost:7860`.

### Method 2: Build and Run Standalone Docker Container
```bash
docker build -t darglobal-concierge .
docker run -p 7860:7860 --env-file .env darglobal-concierge
```

### Method 3: Run Locally (Python 3.11)
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the application
streamlit run src/app.py --server.port=7860
```

---

## 5. Sample Questions for Evaluators

Test the chatbot with these typical buyer and investor queries:

1. **Branded Residences Query:**
   > *"What branded residences do you offer in Dubai?"*
   * *Expected Result:* Details on DaVinci Tower by Pagani, W Residences Downtown, DG1 Living by Gensler, and Trump Tower Dubai with starting prices and links.
2. **Budget-Constrained Investment:**
   > *"Show me apartments under 3,000,000 AED in Dubai."*
   * *Expected Result:* Filters out ultra-luxury penthouses (e.g. 28M AED Pagani) and highlights DG1 Living (1.72M AED), Urban Oasis by Missoni (1.85M AED), and The Astera (1.95M AED).
3. **Regional Villa Search:**
   > *"What luxury villas do you have in Riyadh or Oman?"*
   * *Expected Result:* Features Trump Mansions at Wadi Safar (Riyadh), Wasalt verified 5-bedroom villas in Al-Muhammadiyah, and Trump Cliff Villas at AIDA (Muscat).
4. **Lead Generation & Viewing Request:**
   > *"How do I schedule a private viewing or get the official brochure?"*
   * *Expected Result:* Concierge provides direct guidance and points the user to the sidebar booking form.

---

## 6. Project Structure

```
DarGlobal-Wasalt-AI/
├── .env.example              # Safe configuration template
├── .gitignore                # Production ignore rules (prevents key leaks)
├── ARCHITECTURE.md           # Senior SDE architectural specification
├── Dockerfile                # Production multi-stage container spec (< 500MB)
├── docker-compose.yml        # Local orchestration configuration
├── requirements.txt          # Pinned production dependencies
├── README.md                 # Complete documentation & deployment guide
├── data/
│   ├── processed/
│   │   └── properties.json   # 76 verified property records from DarGlobal & Wasalt
│   └── leads.json            # Captured private client inquiries
└── src/
    ├── app.py                # Main Streamlit web application
    ├── scraper/
    │   ├── models.py         # Unified Pydantic schema
    │   └── pipeline.py       # Scraper & normalization ETL pipeline
    ├── rag/
    │   ├── embeddings.py     # Sentence-transformers CPU wrapper (384-dim)
    │   ├── qdrant_service.py # Qdrant Cloud hybrid search & payload filtering
    │   └── index_catalog.py  # Ingestion script populating Qdrant Cloud
    └── llm/
        └── client.py         # OpenRouter client with auto-failover & streaming
```

---

## 7. Engineering Highlights (Senior SDE Standards)

1. **Deterministic Uptime:** Scraped property snapshot is bundled with the project. The cloud deployment never fails due to scraping blocks, rate limits, or transient timeouts.
2. **True Hybrid Retrieval:** Uses Qdrant Cloud's native payload indexing to ensure mathematical certainty on price caps and bedroom counts before scoring semantic relevance.
3. **Zero API Expenses:** 
   * Embedding: Local ONNX-accelerated CPU embeddings (0 cost, < 25ms latency).
   * Vector DB: Qdrant Cloud Free Tier.
   * LLM: OpenRouter Free Tier with automatic fallback handling.
4. **Production Security:** Non-root Docker execution (`appuser`), dynamic port binding (`$PORT`), sanitized inputs, and `.env` isolation.
