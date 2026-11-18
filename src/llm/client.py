"""Resilient OpenRouter client with multi-model free-tier failover and streaming support."""

import json
import logging
import os
from typing import Any, Generator, Optional
from dotenv import load_dotenv
import httpx

load_dotenv()

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

DEFAULT_FREE_MODELS = [
    "openrouter/free",
    "nvidia/nemotron-3.5-lightning:free",
    "inclusionai/ling-3.2-flash:free",
    "liquid/lfm-3-1.7b:free",
    "particle-ai/particle-1:free",
]

SYSTEM_PROMPT = """You are the Senior Luxury Real Estate Concierge for DarGlobal & Wasalt.
You advise ultra-high-net-worth investors and buyers seeking prime properties in Dubai, Saudi Arabia (Riyadh/Jeddah), Oman (Muscat), and international locations.

GUIDELINES:
1. Ground your answers strictly in the provided PROPERTY CONTEXT below. Do not fabricate prices, availability, or handover dates.
2. DESTINATION / CITY FIDELITY: When the user asks about a specific city or destination (such as Dubai, Riyadh, Muscat/Oman, Spain, Qatar, or London), focus EXCLUSIVELY on properties located in that requested destination. Never present or substitute properties from an unrequested city (e.g. never introduce Riyadh when asked about Dubai).
3. SUPERLATIVES & EXCLUSIVITY: When asked for the 'most expensive', 'highest priced', or 'most exclusive' property, identify the highest-valued asset in the provided context, stating its exact price in AED (and USD), developer, and location.
4. If the user asks to list all properties in a location, enumerate each property provided in the context.
5. Highlight top developments with:
   - Official Project Name and Developer (DarGlobal or Wasalt Partner)
   - Location (City, District, Landmarks)
   - Starting Price in AED (and SAR/USD where relevant)
   - Number of Bedrooms & Handover / Completion Date
   - Key Lifestyle Amenities (branded interiors, canal views, golf access, private pools)
   - Direct link to the project page: [View Official Project](<URL>)
6. Maintain an executive, articulate, and welcoming tone.
7. If a property detail or price is unlisted in context, explicitly inform the user and recommend connecting with a private client advisor.
8. If the user expresses buying interest or asks how to proceed, invite them to use the 'Request Private Viewing' sidebar form to receive the official brochure.
"""


class OpenRouterClient:
    """Manages chat completions via OpenRouter with automatic fallback across free models."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        models_pool: Optional[list[str]] = None,
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required.")

        self.models_pool = models_pool or DEFAULT_FREE_MODELS
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://darglobal.com",
            "X-Title": "DarGlobal Real Estate AI",
        }

    def generate_response(
        self,
        query: str,
        context_properties: list[dict[str, Any]],
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> tuple[str, str]:
        """Generates a complete response, trying models sequentially until success.

        Returns: (assistant_reply, model_used)
        """
        # Format context
        context_text = self._build_context(context_properties)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if conversation_history:
            messages.extend(conversation_history[-6:])  # Last 3 turns

        user_content = f"PROPERTY CONTEXT:\n{context_text}\n\nUSER INQUIRY:\n{query}"
        messages.append({"role": "user", "content": user_content})

        errors = []
        for model in self.models_pool:
            try:
                logger.info(f"Attempting inference with model: {model}")
                with httpx.Client(timeout=30.0) as client:
                    res = client.post(
                        OPENROUTER_URL,
                        headers=self.headers,
                        json={
                            "model": model,
                            "messages": messages,
                            "temperature": 0.4,
                        },
                    )

                if res.status_code == 200:
                    data = res.json()
                    content = data["choices"][0]["message"]["content"]
                    logger.info(f"Inference succeeded with {model}")
                    return content, model
                else:
                    logger.warning(f"Model {model} returned HTTP {res.status_code}: {res.text[:200]}")
                    errors.append(f"{model}: HTTP {res.status_code}")

            except Exception as e:
                logger.warning(f"Model {model} failed with error: {e}")
                errors.append(f"{model}: {str(e)}")

        # Graceful fallback if all free models are throttled
        fallback_msg = (
            "We have retrieved the matching luxury properties from our catalog below. "
            "Our AI concierge is currently experiencing high network demand, but here are the direct project details:\n\n"
        )
        for p in context_properties[:3]:
            fallback_msg += (
                f"### {p.get('title')}\n"
                f"- **Location:** {p.get('city')}, {p.get('country')}\n"
                f"- **Starting Price:** {p.get('price_aed', 0):,.0f} AED\n"
                f"- **Handover:** {p.get('completion_date', 'Inquire')}\n"
                f"- [View Project Page]({p.get('source_url')})\n\n"
            )
        return fallback_msg, "system-fallback"

    def stream_response(
        self,
        query: str,
        context_properties: list[dict[str, Any]],
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> Generator[str, None, None]:
        """Streams response tokens for smooth UI rendering, with model fallback."""
        context_text = self._build_context(context_properties)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if conversation_history:
            messages.extend(conversation_history[-6:])

        user_content = f"PROPERTY CONTEXT:\n{context_text}\n\nUSER INQUIRY:\n{query}"
        messages.append({"role": "user", "content": user_content})

        for model in self.models_pool:
            try:
                logger.info(f"Attempting streaming inference with model: {model}")
                with httpx.Client(timeout=45.0) as client:
                    with client.stream(
                        "POST",
                        OPENROUTER_URL,
                        headers=self.headers,
                        json={
                            "model": model,
                            "messages": messages,
                            "temperature": 0.4,
                            "stream": True,
                        },
                    ) as response:
                        if response.status_code != 200:
                            logger.warning(f"Streaming failed for {model} with status {response.status_code}")
                            continue

                        yielded_anything = False
                        for line in response.iter_lines():
                            if not line or not line.startswith("data: "):
                                continue
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                text = delta.get("content", "")
                                if text:
                                    yielded_anything = True
                                    yield text
                            except Exception:
                                continue

                        if yielded_anything:
                            return

            except Exception as e:
                logger.warning(f"Streaming error on model {model}: {e}")
                continue

        # Fallback to synchronous response if streaming failed
        full_res, _ = self.generate_response(query, context_properties, conversation_history)
        yield full_res

    def _build_context(self, properties: list[dict[str, Any]]) -> str:
        """Converts retrieved properties into structured context blocks."""
        if not properties:
            return "No specific properties found matching exact filters. Provide general guidance."

        lines = []
        for i, p in enumerate(properties, 1):
            lines.append(f"--- PROPERTY {i} ---")
            lines.append(f"Title: {p.get('title')}")
            lines.append(f"Developer: {p.get('developer')}")
            lines.append(f"Source: {p.get('source')}")
            lines.append(f"Type: {p.get('property_type')}")
            lines.append(f"Location: {p.get('city')}, {p.get('country')}" + (f" ({p.get('district')})" if p.get('district') else ""))
            if p.get("brand_partner"):
                lines.append(f"Branding: {p.get('brand_partner')}")
            if p.get("price_aed"):
                lines.append(f"Price AED: {p.get('price_aed'):,.0f} AED (Original: {p.get('price', 0):,.0f} {p.get('currency', 'AED')})")
            if p.get("bedrooms"):
                lines.append(f"Bedrooms: {p.get('bedrooms')}")
            if p.get("completion_date"):
                lines.append(f"Handover Date: {p.get('completion_date')}")
            if p.get("amenities"):
                lines.append(f"Amenities: {', '.join(p.get('amenities', []))}")
            lines.append(f"Project URL: {p.get('source_url')}")
            lines.append(f"Summary: {p.get('description')}\n")
        return "\n".join(lines)
