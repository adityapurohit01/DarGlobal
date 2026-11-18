"""Indexes processed properties into Qdrant Cloud with dense vectors and payload metadata."""

import json
import logging
from pathlib import Path
from dotenv import load_dotenv

from src.rag.embeddings import EmbeddingService
from src.rag.qdrant_service import QdrantService
from src.scraper.models import PropertyRecord

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def index_all(recreate: bool = True) -> int:
    """Reads properties.json, generates embeddings, and uploads to Qdrant Cloud."""
    data_path = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "properties.json"
    if not data_path.exists():
        raise FileNotFoundError(f"Missing {data_path}. Run pipeline first.")

    with open(data_path, encoding="utf-8") as f:
        raw_items = json.load(f)

    records = [PropertyRecord(**item) for item in raw_items]
    logger.info(f"Loaded {len(records)} property records from {data_path}")

    # Generate contextual embedding texts
    texts = [r.to_embedding_text() for r in records]

    # Generate vectors
    embedder = EmbeddingService()
    logger.info("Computing dense embeddings...")
    vectors = embedder.embed_batch(texts, batch_size=32)
    logger.info(f"Generated {len(vectors)} embeddings of dimension {len(vectors[0])}")

    # Upsert to Qdrant Cloud
    qdrant = QdrantService()
    if recreate:
        qdrant.init_collection(recreate=True)
    count = qdrant.upsert_records([r.model_dump() for r in records], vectors)
    logger.info(f"Indexing complete! {count} properties are live in Qdrant Cloud.")
    return count


if __name__ == "__main__":
    index_all(recreate=True)
