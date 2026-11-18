"""Unified property schema for DarGlobal and Wasalt real estate data."""

from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel, Field


class PropertyRecord(BaseModel):
    """Normalized real estate listing or development project."""

    id: str = Field(..., description="Unique deterministic identifier")
    source: Literal["DarGlobal", "Wasalt"] = Field(..., description="Data source origin")
    title: str = Field(..., description="Project or property title")
    developer: str = Field(default="DarGlobal", description="Developer or agency name")
    property_type: str = Field(default="Apartment", description="Apartment, Villa, Penthouse, etc.")
    country: str = Field(..., description="Country name (e.g. United Arab Emirates, Saudi Arabia, Oman)")
    city: str = Field(..., description="City name (e.g. Dubai, Riyadh, Muscat)")
    district: Optional[str] = Field(default=None, description="Neighborhood or community name")
    price: Optional[float] = Field(default=None, description="Original listing or starting price")
    currency: str = Field(default="AED", description="Currency code (AED, SAR, USD)")
    price_aed: Optional[float] = Field(default=None, description="Normalized price in AED for filtering")
    bedrooms: Optional[int] = Field(default=None, description="Number of bedrooms (None for multi-unit masterplans)")
    completion_date: Optional[str] = Field(default=None, description="Handover or completion date/year")
    brand_partner: Optional[str] = Field(default=None, description="Luxury co-branding partner (e.g. Pagani, Missoni, Trump)")
    amenities: list[str] = Field(default_factory=list, description="Key amenities and lifestyle highlights")
    description: str = Field(..., description="Comprehensive descriptive text for semantic indexing")
    image_url: Optional[str] = Field(default=None, description="High-resolution hero image URL")
    source_url: str = Field(..., description="Public URL to the property/project page")
    scraped_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_embedding_text(self) -> str:
        """Generates rich contextual text for dense vector embedding."""
        parts = [
            f"Title: {self.title}",
            f"Source: {self.source}",
            f"Developer: {self.developer}",
            f"Property Type: {self.property_type}",
            f"Location: {self.city}, {self.country}" + (f" ({self.district})" if self.district else ""),
        ]
        if self.brand_partner:
            parts.append(f"Luxury Brand Partner: {self.brand_partner}")
        if self.price_aed:
            parts.append(f"Price: {self.price_aed:,.0f} AED ({self.price:,.0f} {self.currency})")
        if self.bedrooms:
            parts.append(f"Bedrooms: {self.bedrooms}")
        if self.completion_date:
            parts.append(f"Handover Date: {self.completion_date}")
        if self.amenities:
            parts.append(f"Amenities: {', '.join(self.amenities)}")
        parts.append(f"Description: {self.description}")
        return "\n".join(parts)
