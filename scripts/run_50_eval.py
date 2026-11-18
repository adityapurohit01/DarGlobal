"""End-to-end evaluation suite: Tests RAG retrieval and LLM generation across 50 questions."""

import json
import logging
import os
import time
from pathlib import Path
from dotenv import load_dotenv

from src.rag.embeddings import EmbeddingService
from src.rag.qdrant_service import QdrantService
from src.llm.client import OpenRouterClient

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# 50 Comprehensive Evaluation Questions across 5 Categories
TEST_QUESTIONS = [
    # Category 1: DarGlobal Dubai Flagships (1-10)
    {
        "id": 1,
        "category": "Dubai Flagships",
        "question": "What is DG1 Living by DarGlobal and where is it located in Dubai?",
        "expected_entity": "DG1",
        "expected_location": "Business Bay",
    },
    {
        "id": 2,
        "category": "Dubai Flagships",
        "question": "Tell me about Da Vinci Tower with interiors by Pagani. What is the starting price?",
        "expected_entity": "Da Vinci Tower",
        "expected_brand": "Pagani",
    },
    {
        "id": 3,
        "category": "Dubai Flagships",
        "question": "Are there any villas available in Dubai developed by DarGlobal?",
        "expected_entity": "D-Villas At Jumeirah Golf Estates",
        "expected_type": "Villas",
    },
    {
        "id": 4,
        "category": "Dubai Flagships",
        "question": "What are the key features of W Residences Downtown Dubai?",
        "expected_entity": "W Residences",
        "expected_brand": "W Hotels",
    },
    {
        "id": 5,
        "category": "Dubai Flagships",
        "question": "Can I buy a Trump-branded residence in Dubai through DarGlobal?",
        "expected_entity": "Trump International Hotel & Tower Dubai",
        "expected_brand": "Trump",
    },
    {
        "id": 6,
        "category": "Dubai Flagships",
        "question": "What is The Pagani Penthouse and what luxury amenities does it offer?",
        "expected_entity": "The Pagani Penthouse",
        "expected_brand": "Pagani",
    },
    {
        "id": 7,
        "category": "Dubai Flagships",
        "question": "Tell me about Urban Oasis by Missoni in Business Bay. Is it completed?",
        "expected_entity": "Urban Oasis",
        "expected_brand": "Missoni",
    },
    {
        "id": 8,
        "category": "Dubai Flagships",
        "question": "What is the handover date for DG1 Living in Dubai?",
        "expected_entity": "DG1",
        "expected_handover": "December 2027",
    },
    {
        "id": 9,
        "category": "Dubai Flagships",
        "question": "What views does DG1 Living offer in Business Bay?",
        "expected_entity": "DG1",
        "expected_feature": "Dubai Canal",
    },
    {
        "id": 10,
        "category": "Dubai Flagships",
        "question": "Which DarGlobal properties in Dubai are located directly on the Dubai Water Canal?",
        "expected_entity": "Da Vinci Tower",
    },

    # Category 2: Regional & International Developments (11-20)
    {
        "id": 11,
        "category": "Regional & International",
        "question": "What is the AIDA project in Oman developed by DarGlobal?",
        "expected_entity": "AIDA",
        "expected_location": "Oman",
    },
    {
        "id": 12,
        "category": "Regional & International",
        "question": "Are there Trump villas available in Oman?",
        "expected_entity": "Trump Cliff Villas",
        "expected_location": "Oman",
    },
    {
        "id": 13,
        "category": "Regional & International",
        "question": "Does DarGlobal have projects in Saudi Arabia?",
        "expected_entity": "Trump Mansions",
        "expected_location": "Saudi Arabia",
    },
    {
        "id": 14,
        "category": "Regional & International",
        "question": "Tell me about Tierra Viva in Spain. Which luxury brand is it partnered with?",
        "expected_entity": "Tierra Viva",
        "expected_brand": "Lamborghini",
    },
    {
        "id": 15,
        "category": "Regional & International",
        "question": "What is Marea in Spain and who designed the interiors?",
        "expected_entity": "Marea",
        "expected_brand": "Missoni",
    },
    {
        "id": 16,
        "category": "Regional & International",
        "question": "What development does DarGlobal have in Qatar?",
        "expected_entity": "Trump International Simaisma",
        "expected_location": "Qatar",
    },
    {
        "id": 17,
        "category": "Regional & International",
        "question": "What is The Astera on Al Marjan Island and who designed it?",
        "expected_entity": "The Astera",
        "expected_brand": "Aston Martin",
    },
    {
        "id": 18,
        "category": "Regional & International",
        "question": "What are the Marriott Residences in AIDA Oman?",
        "expected_entity": "Marriott Residences",
        "expected_location": "Oman",
    },
    {
        "id": 19,
        "category": "Regional & International",
        "question": "Does DarGlobal have any developments in the United Kingdom?",
        "expected_entity": "United Kingdom",
    },
    {
        "id": 20,
        "category": "Regional & International",
        "question": "Tell me about Trump Tower Jeddah. What are its highlights?",
        "expected_entity": "Trump Tower Jeddah",
        "expected_location": "Jeddah",
    },

    # Category 3: Wasalt Saudi Arabia Marketplace (21-30)
    {
        "id": 21,
        "category": "Wasalt Marketplace",
        "question": "What properties are listed on Wasalt in Riyadh?",
        "expected_source": "Wasalt",
        "expected_location": "Riyadh",
    },
    {
        "id": 22,
        "category": "Wasalt Marketplace",
        "question": "Find me villas for sale in Riyadh through Wasalt.",
        "expected_source": "Wasalt",
        "expected_type": "Villa",
    },
    {
        "id": 23,
        "category": "Wasalt Marketplace",
        "question": "Are there properties available in Al-Muhammadiyah district in Riyadh?",
        "expected_source": "Wasalt",
        "expected_district": "Al-Muhammadiyah",
    },
    {
        "id": 24,
        "category": "Wasalt Marketplace",
        "question": "What is the price of the 5-bedroom villa in Al-Muhammadiyah on Wasalt?",
        "expected_source": "Wasalt",
        "expected_district": "Al-Muhammadiyah",
    },
    {
        "id": 25,
        "category": "Wasalt Marketplace",
        "question": "Find me properties in Al-Faruq district in Riyadh on Wasalt.",
        "expected_source": "Wasalt",
        "expected_district": "Al-Faruq",
    },
    {
        "id": 26,
        "category": "Wasalt Marketplace",
        "question": "Does Wasalt have listings in Jeddah or Western Province?",
        "expected_source": "Wasalt",
    },
    {
        "id": 27,
        "category": "Wasalt Marketplace",
        "question": "Are Wasalt listings verified by REGA (Real Estate General Authority)?",
        "expected_source": "Wasalt",
    },
    {
        "id": 28,
        "category": "Wasalt Marketplace",
        "question": "What currency are Wasalt listings typically quoted in?",
        "expected_currency": "SAR",
    },
    {
        "id": 29,
        "category": "Wasalt Marketplace",
        "question": "Can I find ready-to-move-in properties on Wasalt?",
        "expected_source": "Wasalt",
    },
    {
        "id": 30,
        "category": "Wasalt Marketplace",
        "question": "What is the project 'Mashroua Sittat Amyal' (Six Miles Project) listed on Wasalt?",
        "expected_source": "Wasalt",
    },

    # Category 4: Numerical, Budget & Bedroom Constraints (31-40)
    {
        "id": 31,
        "category": "Constraints & Filters",
        "question": "Show me properties in Dubai under 2,000,000 AED.",
        "filter_city": "Dubai",
        "filter_max_price": 2000000.0,
    },
    {
        "id": 32,
        "category": "Constraints & Filters",
        "question": "Show me ultra-luxury properties priced above 10,000,000 AED.",
        "expected_min_price": 10000000.0,
    },
    {
        "id": 33,
        "category": "Constraints & Filters",
        "question": "Find me 4-bedroom luxury villas in Dubai or Riyadh.",
        "expected_type": "Villas",
        "filter_beds": 4,
    },
    {
        "id": 34,
        "category": "Constraints & Filters",
        "question": "What can I buy with a budget of 3,000,000 AED in Dubai?",
        "filter_city": "Dubai",
        "filter_max_price": 3000000.0,
    },
    {
        "id": 35,
        "category": "Constraints & Filters",
        "question": "What properties are available between 4,000,000 AED and 7,000,000 AED?",
    },
    {
        "id": 36,
        "category": "Constraints & Filters",
        "question": "Find me 1-bedroom investment apartments in Dubai.",
        "filter_city": "Dubai",
    },
    {
        "id": 37,
        "category": "Constraints & Filters",
        "question": "Show me properties with completion scheduled around 2026 or 2027.",
    },
    {
        "id": 38,
        "category": "Constraints & Filters",
        "question": "Show me completed or ready-to-move-in properties in Dubai or Riyadh.",
    },
    {
        "id": 39,
        "category": "Constraints & Filters",
        "question": "What is the most accessible luxury entry price in DarGlobal's portfolio?",
        "expected_entity": "AIDA",
    },
    {
        "id": 40,
        "category": "Constraints & Filters",
        "question": "Find me properties under 1,500,000 AED.",
        "filter_max_price": 1500000.0,
    },

    # Category 5: Advisory, Personas & Edge Cases (41-50)
    {
        "id": 41,
        "category": "Advisory & Domain",
        "question": "Which property offers the best golf course views and lifestyle?",
        "expected_amenity": "golf",
    },
    {
        "id": 42,
        "category": "Advisory & Domain",
        "question": "I am an automotive enthusiast looking for supercar-branded residences. What do you recommend?",
        "expected_brands": ["Pagani", "Aston Martin", "Lamborghini"],
    },
    {
        "id": 43,
        "category": "Advisory & Domain",
        "question": "Which developments are best suited for waterfront or canal living?",
        "expected_feature": "canal",
    },
    {
        "id": 44,
        "category": "Advisory & Domain",
        "question": "What payment plan or schedule is typical for DarGlobal developments like DG1?",
    },
    {
        "id": 45,
        "category": "Advisory & Domain",
        "question": "How do I request an official brochure or arrange a private viewing?",
    },
    {
        "id": 46,
        "category": "Advisory & Domain",
        "question": "Do you have any properties in New York or Paris?",
    },
    {
        "id": 47,
        "category": "Advisory & Domain",
        "question": "Can you convert property prices from AED to USD or SAR?",
    },
    {
        "id": 48,
        "category": "Advisory & Domain",
        "question": "What are the lifestyle amenities at W Residences Downtown Dubai?",
        "expected_entity": "W Residences",
    },
    {
        "id": 49,
        "category": "Advisory & Domain",
        "question": "How does Wasalt help buyers verify property ownership and listings in Saudi Arabia?",
    },
    {
        "id": 50,
        "category": "Advisory & Domain",
        "question": "Compare DG1 Living in Business Bay and DaVinci Tower by Pagani for an investor.",
        "expected_entities": ["DG1", "Da Vinci Tower"],
    },
]


def run_eval():
    """Executes the full 50-question evaluation."""
    output_dir = Path(__file__).resolve().parent.parent / "data"
    output_path = output_dir / "eval_results.json"

    logger.info("Initializing services for evaluation...")
    embedder = EmbeddingService()
    qdrant = QdrantService()
    llm = OpenRouterClient()

    results = []
    total = len(TEST_QUESTIONS)

    logger.info(f"Starting test suite of {total} questions...")

    for i, t in enumerate(TEST_QUESTIONS, 1):
        q_id = t["id"]
        cat = t["category"]
        query = t["question"]

        logger.info(f"[{i}/{total}] Testing Q{q_id} ({cat}): '{query}'")

        start_time = time.time()

        # Step 1: Embed query
        vec = embedder.embed_text(query)

        # Step 2: Hybrid Search in Qdrant Cloud
        city_f = t.get("filter_city")
        price_f = t.get("filter_max_price")
        beds_f = t.get("filter_beds")

        matched = qdrant.search(
            query_vector=vec,
            city=city_f,
            max_price_aed=price_f,
            min_bedrooms=beds_f,
            limit=3,
        )

        retrieval_ms = round((time.time() - start_time) * 1000, 1)

        # Step 3: LLM Inference with fallback
        llm_start = time.time()
        answer, model_used = llm.generate_response(query, matched)
        llm_ms = round((time.time() - llm_start) * 1000, 1)
        total_ms = round((time.time() - start_time) * 1000, 1)

        # Automated grounding / quality checks
        retrieved_titles = [m.get("title") for m in matched]
        matched_scores = [m.get("_score") for m in matched]

        # Check entity recall
        expected_entity = t.get("expected_entity")
        entity_recalled = True
        if expected_entity:
            entity_recalled = any(expected_entity.lower() in (t or "").lower() for t in retrieved_titles)

        # Check price filter validity
        filter_valid = True
        if price_f:
            for m in matched:
                p_aed = m.get("price_aed")
                if p_aed and p_aed > price_f:
                    filter_valid = False

        record = {
            "id": q_id,
            "category": cat,
            "question": query,
            "retrieval_time_ms": retrieval_ms,
            "llm_time_ms": llm_ms,
            "total_time_ms": total_ms,
            "model_used": model_used,
            "retrieved_count": len(matched),
            "top_matches": retrieved_titles,
            "top_scores": matched_scores,
            "entity_recalled": entity_recalled,
            "filter_valid": filter_valid,
            "answer": answer,
        }
        results.append(record)

        # Save incremental progress
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        logger.info(f"Q{q_id} done in {total_ms}ms (LLM: {model_used}, Top: {retrieved_titles[:2]})")

        # Brief rate limit safety pause between LLM calls
        time.sleep(1.0)

    logger.info(f"Evaluation complete! 50/50 questions saved to {output_path}")
    return output_path


if __name__ == "__main__":
    run_eval()
