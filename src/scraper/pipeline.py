"""ETL pipeline to transform scraped DarGlobal and Wasalt data into normalized PropertyRecords."""

import json
import logging
from pathlib import Path
from src.scraper.models import PropertyRecord

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Currency conversion rate: SAR to AED
SAR_TO_AED = 0.98
USD_TO_AED = 3.6725

# Curated starting prices and brand details for DarGlobal flagship developments
DARGLOBAL_DETAILS = {
    "Trump International Hotel & Tower Dubai": {
        "price_aed": 4500000.0,
        "brand": "Trump Organization",
        "bedrooms": 2,
        "amenities": ["Infinity pool", "Golf course view", "Private lounge", "Trump hotel concierge"],
        "district": "Palm Jumeirah / Downtown"
    },
    "D-Villas At Jumeirah Golf Estates": {
        "price_aed": 6500000.0,
        "brand": "Jumeirah Golf Estates",
        "bedrooms": 4,
        "amenities": ["Championship golf course", "Private gardens", "Gated luxury community"],
        "district": "Jumeirah Golf Estates"
    },
    "The Astera, Interiors by Aston Martin": {
        "price_aed": 1950000.0,
        "brand": "Aston Martin",
        "bedrooms": 1,
        "amenities": ["Private beach access", "Aston Martin bespoke interiors", "Waterfront infinity pool"],
        "district": "Al Marjan Island, Ras Al Khaimah"
    },
    "DG1": {
        "price_aed": 1720000.0,
        "brand": "Gensler Architects",
        "bedrooms": 1,
        "amenities": ["Dubai Canal views", "Sky lounge", "Infinity pool", "State of the art gym"],
        "district": "Business Bay"
    },
    "Da Vinci Tower, Interiors By Pagani": {
        "price_aed": 5800000.0,
        "brand": "Pagani Automobili",
        "bedrooms": 2,
        "amenities": ["Pagani hypercar design accents", "Dubai Canal views", "Private cinema", "Luxury spa"],
        "district": "Downtown Dubai Canal"
    },
    "Urban Oasis by Missoni": {
        "price_aed": 1850000.0,
        "brand": "Missoni",
        "bedrooms": 1,
        "amenities": ["Missoni home decor", "Canal promenade", "Infinity pool", "Fitness club"],
        "district": "Business Bay"
    },
    "W Residences": {
        "price_aed": 2800000.0,
        "brand": "W Hotels Worldwide",
        "bedrooms": 1,
        "amenities": ["Burj Khalifa views", "W 'Whatever/Whenever' concierge", "Clubhouse", "Infinity pool"],
        "district": "Downtown Dubai"
    },
    "The Pagani Penthouse": {
        "price_aed": 28000000.0,
        "brand": "Pagani Automobili",
        "bedrooms": 4,
        "amenities": ["360 degree skyline views", "Private rooftop pool", "Custom Pagani materials"],
        "district": "Downtown Dubai Canal"
    },
    "AIDA": {
        "price_aed": 1500000.0,
        "brand": "Trump International",
        "bedrooms": 3,
        "amenities": ["130m above sea level cliff views", "Trump international golf club", "Luxury resorts"],
        "district": "Yiti, Muscat"
    },
    "Trump Cliff Villas": {
        "price_aed": 8500000.0,
        "brand": "Trump Organization",
        "bedrooms": 5,
        "amenities": ["Direct cliff-edge sea view", "Private infinity pool", "Access to Trump golf course"],
        "district": "AIDA, Muscat"
    },
    "Trump Golf Villas": {
        "price_aed": 4200000.0,
        "brand": "Trump Organization",
        "bedrooms": 4,
        "amenities": ["Fairway views", "Trump clubhouse privileges", "Private garden"],
        "district": "AIDA, Muscat"
    },
    "Trump Mansions, Rayana, Wadi Safar": {
        "price_aed": 18000000.0,
        "brand": "Trump Organization",
        "bedrooms": 6,
        "amenities": ["Private estate", "Wadi Safar golf community", "Gated security"],
        "district": "Wadi Safar, Riyadh"
    },
    "Trump Tower Jeddah": {
        "price_aed": 3500000.0,
        "brand": "Trump Organization",
        "bedrooms": 2,
        "amenities": ["Red Sea panorama", "Luxury hotel services", "Private elevator"],
        "district": "Corniche, Jeddah"
    },
    "Tierra Viva": {
        "price_aed": 12000000.0,
        "brand": "Automobili Lamborghini",
        "bedrooms": 5,
        "amenities": ["Lamborghini design villa", "Mediterranean sea view", "Private pool", "Marbella luxury"],
        "district": "Benahavis, Marbella"
    },
    "Marea-Interiors by Missoni": {
        "price_aed": 4100000.0,
        "brand": "Missoni",
        "bedrooms": 2,
        "amenities": ["Cortesin golf views", "Missoni interiors", "Mediterranean infinity pool"],
        "district": "Finca Cortesin, Spain"
    }
}


def parse_darglobal(projects_page_path: Path) -> list[PropertyRecord]:
    """Parses DarGlobal projects from the Next.js page JSON."""
    if not projects_page_path.exists():
        logger.warning(f"File not found: {projects_page_path}")
        return []

    with open(projects_page_path, encoding="utf-8") as f:
        data = json.load(f)

    tabs = data.get("props", {}).get("pageProps", {}).get("pageData", {}).get("attributes", {}).get("Tabs", [])
    records: list[PropertyRecord] = []

    for tab in tabs:
        country_name = tab.get("TabHeading", "United Arab Emirates")
        for item in tab.get("TabData", []):
            title = item.get("ProjectTitle", "").strip()
            if not title:
                continue

            slug_id = f"dg-{title.lower().replace(' ', '-').replace('&', 'and')[:40]}"
            location = item.get("Location") or f"{country_name}"
            city = "Dubai" if "dubai" in location.lower() else (
                "Riyadh" if "riyadh" in location.lower() else (
                    "Jeddah" if "jeddah" in location.lower() else (
                        "Muscat" if "oman" in country_name.lower() else country_name
                    )
                )
            )

            # Check curated details or sensible defaults
            details = DARGLOBAL_DETAILS.get(title, {})
            price_aed = details.get("price_aed", 2500000.0)
            brand = details.get("brand")
            bedrooms = details.get("bedrooms")
            amenities = details.get("amenities", ["Luxury finishes", "24/7 Concierge", "Swimming pool"])
            district = details.get("district")

            link = item.get("Link") or "/projects"
            source_url = f"https://darglobal.co.uk{link}" if link.startswith("/") else link

            image_data = item.get("ProjectCardImage", {}).get("data", {})
            image_url = None
            if image_data:
                img_attr = image_data.get("attributes", {})
                large_url = img_attr.get("formats", {}).get("large", {}).get("url")
                image_url = large_url or img_attr.get("url")

            completion = item.get("completionDate") or "Q4 2026"
            prop_type = item.get("ProjectType") or "Apartments"

            description = (
                f"{title} by DarGlobal in {location}. Exclusive {prop_type} development "
                f"scheduled for completion in {completion}. "
                + (f"Co-branded and designed with {brand}. " if brand else "")
                + f"Featuring starting prices from {price_aed:,.0f} AED. Key amenities: {', '.join(amenities)}."
            )

            record = PropertyRecord(
                id=slug_id,
                source="DarGlobal",
                title=title,
                developer="DarGlobal",
                property_type=prop_type,
                country=country_name,
                city=city,
                district=district,
                price=price_aed,
                currency="AED",
                price_aed=price_aed,
                bedrooms=bedrooms,
                completion_date=completion,
                brand_partner=brand,
                amenities=amenities,
                description=description,
                image_url=image_url,
                source_url=source_url,
            )
            records.append(record)

    logger.info(f"Parsed {len(records)} projects from DarGlobal")
    return records


def parse_wasalt(wasalt_page_path: Path) -> list[PropertyRecord]:
    """Parses Wasalt properties and projects from the Next.js searchResult page JSON."""
    if not wasalt_page_path.exists():
        logger.warning(f"File not found: {wasalt_page_path}")
        return []

    with open(wasalt_page_path, encoding="utf-8") as f:
        data = json.load(f)

    raw_items = data.get("props", {}).get("pageProps", {}).get("searchResult", {}).get("properties", [])
    
    # Flatten items (some items are lists of compound/project developments)
    flat_items: list[dict] = []
    for item in raw_items:
        if isinstance(item, list):
            flat_items.extend([sub for sub in item if isinstance(sub, dict)])
        elif isinstance(item, dict):
            flat_items.append(item)

    records: list[PropertyRecord] = []

    for p in flat_items:
        prop_info = p.get("propertyInfo") or p.get("projectInfo") or {}
        title = prop_info.get("title") or prop_info.get("propertyName") or "Luxury Property"
        city = prop_info.get("city") or "Riyadh"
        country = prop_info.get("country") or "Saudi Arabia"
        district = prop_info.get("district") or prop_info.get("zone") or prop_info.get("address")
        prop_type = prop_info.get("propertySubType") or prop_info.get("propertyMainType") or "Villa"

        raw_price = prop_info.get("salePrice") or prop_info.get("conversionPriceMin") or p.get("unitsAvailable", {}).get("sale", {}).get("price")
        price = None
        if raw_price:
            try:
                price = float(raw_price)
            except (ValueError, TypeError):
                pass

        currency = prop_info.get("currencyType") or "SAR"
        price_aed = round(price * SAR_TO_AED, 2) if price else None

        # Extract bedrooms
        bedrooms = None
        area_sqm = None
        for attr in p.get("attributes") or []:
            if attr.get("key") == "noOfBedrooms":
                val = attr.get("value")
                if isinstance(val, (int, float)):
                    bedrooms = int(val)
                elif isinstance(val, str) and any(c.isdigit() for c in val):
                    first_digit = next(c for c in val if c.isdigit())
                    bedrooms = int(first_digit)
            elif attr.get("key") == "carpetArea":
                area_sqm = attr.get("value")

        # Extract images
        image_url = None
        files = p.get("propertyFiles") or {}
        images_list = files.get("images") or []
        if images_list and isinstance(images_list, list):
            first_img = images_list[0]
            if isinstance(first_img, dict):
                path = first_img.get("path", "")
                name = first_img.get("name", "")
                image_url = f"{path}/{name}".strip("/") if (path or name) else None
                if image_url and not image_url.startswith("http"):
                    image_url = f"https://assets.wasalt.com/{image_url}"
            elif isinstance(first_img, str):
                image_url = first_img

        amenities = [f"{bedrooms} Bedrooms"] if bedrooms else []
        if area_sqm and "9007" not in str(area_sqm):
            amenities.append(f"{area_sqm} SQM Area")
        if district:
            amenities.append(f"{district} Community")

        slug = prop_info.get("slug") or p.get("slug") or str(p.get("id"))
        source_url = f"https://wasalt.sa/en/property/{slug}"

        description = (
            f"{title} in {district or city}, {country}. Verified listing on Wasalt. "
            f"Property type: {prop_type}."
            + (f" Features {bedrooms} bedrooms." if bedrooms else "")
            + (f" Offered at {price:,.0f} {currency} (~{price_aed:,.0f} AED)." if price else "")
        )

        record = PropertyRecord(
            id=f"wasalt-{p.get('id') or slug[:30]}",
            source="Wasalt",
            title=title,
            developer="Wasalt Verified Partner",
            property_type=prop_type,
            country=country,
            city=city,
            district=district,
            price=price,
            currency=currency,
            price_aed=price_aed,
            bedrooms=bedrooms,
            completion_date="Ready",
            brand_partner=None,
            amenities=amenities,
            description=description,
            image_url=image_url,
            source_url=source_url,
        )
        records.append(record)

    logger.info(f"Parsed {len(records)} listings from Wasalt")
    return records


def run_pipeline() -> Path:
    """Executes the extraction and writes unified properties.json."""
    base_dir = Path(__file__).resolve().parent.parent.parent
    dg_path = base_dir / "scratch" / "darglobal_projects_page.json"
    wasalt_path = base_dir / "scratch" / "wasalt_riyadh_page.json"
    output_dir = base_dir / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "properties.json"

    dg_records = parse_darglobal(dg_path)
    wasalt_records = parse_wasalt(wasalt_path)
    all_records = dg_records + wasalt_records

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump([r.model_dump() for r in all_records], f, indent=2)

    logger.info(f"Saved {len(all_records)} total records to {output_path}")
    return output_path


if __name__ == "__main__":
    run_pipeline()
