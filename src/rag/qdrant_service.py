"""Qdrant Cloud vector database service for hybrid search and payload filtering."""

import logging
import os
from typing import Any, Optional
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_COLLECTION = "darglobal_properties"
VECTOR_SIZE = 384


class QdrantService:
    """Manages collection schema, payload indexing, vector upserts, and filtered queries."""

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        collection_name: Optional[str] = None,
    ):
        self.url = url or os.getenv(
            "QDRANT_URL",
            "https://072171e4-90fb-49cd-849d-0a1afde67e8d.ap-northeast-2-0.aws.cloud.qdrant.io",
        )
        self.api_key = api_key or os.getenv("QDRANT_API_KEY")
        self.collection_name = collection_name or os.getenv("QDRANT_COLLECTION", DEFAULT_COLLECTION)

        logger.info(f"Connecting to Qdrant Cloud at {self.url} (collection: {self.collection_name})")
        self.client = QdrantClient(
            url=self.url,
            api_key=self.api_key,
            check_compatibility=False,
            timeout=25.0,
        )

    def init_collection(self, recreate: bool = False) -> None:
        """Initializes the collection and creates payload field indexes for filtering."""
        collections = [c.name for c in self.client.get_collections().collections]

        if self.collection_name in collections:
            if not recreate:
                logger.info(f"Collection '{self.collection_name}' already exists.")
                return
            logger.info(f"Recreating collection '{self.collection_name}'...")
            self.client.delete_collection(self.collection_name)

        logger.info(f"Creating collection '{self.collection_name}' (vector size: {VECTOR_SIZE})...")
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
        )

        # Create payload indexes for high-speed faceted search
        for field in ["city", "country", "developer", "property_type"]:
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
            except Exception as e:
                logger.debug(f"Payload index on {field}: {e}")

        for num_field in ["price_aed", "bedrooms"]:
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=num_field,
                    field_schema=models.PayloadSchemaType.FLOAT,
                )
            except Exception as e:
                logger.debug(f"Payload index on {num_field}: {e}")

        logger.info(f"Collection '{self.collection_name}' initialized with payload indexes.")

    def upsert_records(
        self,
        records: list[dict[str, Any]],
        vectors: list[list[float]],
        batch_size: int = 50,
    ) -> int:
        """Uploads property payloads and corresponding dense vectors to Qdrant Cloud."""
        self.init_collection(recreate=False)
        total = len(records)
        points: list[models.PointStruct] = []

        for idx, (rec, vec) in enumerate(zip(records, vectors)):
            points.append(
                models.PointStruct(
                    id=idx + 1,
                    vector=vec,
                    payload=rec,
                )
            )

        logger.info(f"Upserting {total} points into collection '{self.collection_name}'...")
        for i in range(0, total, batch_size):
            chunk = points[i : i + batch_size]
            self.client.upsert(
                collection_name=self.collection_name,
                points=chunk,
                wait=True,
            )

        logger.info(f"Successfully upserted {total} records.")
        return total

    def search(
        self,
        query_vector: list[float],
        city: Optional[str] = None,
        max_price_aed: Optional[float] = None,
        min_bedrooms: Optional[int] = None,
        property_type: Optional[str] = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Executes hybrid retrieval: metadata filtering combined with vector cosine search."""
        must_filters: list[models.Condition] = []

        if city and city != "All":
            must_filters.append(
                models.FieldCondition(
                    key="city",
                    match=models.MatchValue(value=city),
                )
            )

        if max_price_aed and max_price_aed > 0:
            must_filters.append(
                models.FieldCondition(
                    key="price_aed",
                    range=models.Range(lte=max_price_aed),
                )
            )

        if min_bedrooms and min_bedrooms > 0:
            must_filters.append(
                models.FieldCondition(
                    key="bedrooms",
                    range=models.Range(gte=min_bedrooms),
                )
            )

        if property_type and property_type != "All":
            must_filters.append(
                models.FieldCondition(
                    key="property_type",
                    match=models.MatchValue(value=property_type),
                )
            )

        qdrant_filter = models.Filter(must=must_filters) if must_filters else None

        res = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=qdrant_filter,
            limit=limit,
            with_payload=True,
        )

        matches: list[dict[str, Any]] = []
        for hit in res.points:
            item = dict(hit.payload or {})
            item["_score"] = round(hit.score, 4)
            matches.append(item)

        return matches
