"""
Google Maps / Places Tool
Find businesses, doctors, restaurants, and any location-based services.
Provides ratings, reviews, contact info, and directions.
"""
import logging
from typing import Optional
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

PLACES_BASE_URL = "https://maps.googleapis.com/maps/api/place"


async def search_nearby(
    query: str,
    location: Optional[str] = None,
    radius_meters: int = 10000,
    min_rating: float = 0.0,
) -> dict:
    """
    Search for places near a location using Google Places API.

    Args:
        query: What to search for, e.g., "dentist", "pizza restaurant"
        location: "lat,lng" string. If None, uses text search without location bias.
        radius_meters: Search radius in meters (default 10km)
        min_rating: Minimum rating filter (0-5)

    Returns:
        dict with 'places' list containing name, address, rating, reviews, etc.
    """
    if not settings.google_maps_api_key:
        return {
            "places": [],
            "error": "Google Maps API key not configured. Set GOOGLE_MAPS_API_KEY in .env",
        }

    try:
        async with httpx.AsyncClient() as client:
            params = {
                "query": query,
                "key": settings.google_maps_api_key,
            }
            if location:
                params["location"] = location
                params["radius"] = radius_meters

            response = await client.get(
                f"{PLACES_BASE_URL}/textsearch/json",
                params=params,
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "OK":
                return {
                    "places": [],
                    "error": f"Google Places API error: {data.get('status')}",
                }

            places = []
            for result in data.get("results", []):
                rating = result.get("rating", 0)
                if rating < min_rating:
                    continue

                places.append({
                    "name": result.get("name", ""),
                    "address": result.get("formatted_address", ""),
                    "rating": rating,
                    "total_reviews": result.get("user_ratings_total", 0),
                    "place_id": result.get("place_id", ""),
                    "is_open": result.get("opening_hours", {}).get("open_now"),
                    "types": result.get("types", []),
                    "location": result.get("geometry", {}).get("location", {}),
                    "price_level": result.get("price_level"),
                    "google_maps_url": f"https://www.google.com/maps/place/?q=place_id:{result.get('place_id', '')}",
                })

            # Sort by rating (highest first)
            places.sort(key=lambda x: (x["rating"], x["total_reviews"]), reverse=True)

            return {"places": places[:10]}

    except Exception as e:
        logger.error(f"Google Maps search error: {e}")
        return {"places": [], "error": str(e)}


async def get_place_details(place_id: str) -> dict:
    """
    Get detailed information about a specific place.
    Includes phone number, website, reviews, and hours.
    """
    if not settings.google_maps_api_key:
        return {"error": "Google Maps API key not configured"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{PLACES_BASE_URL}/details/json",
                params={
                    "place_id": place_id,
                    "fields": "name,formatted_address,formatted_phone_number,"
                              "international_phone_number,website,rating,"
                              "user_ratings_total,reviews,opening_hours,"
                              "url,business_status,types",
                    "key": settings.google_maps_api_key,
                },
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "OK":
                return {"error": f"Place details error: {data.get('status')}"}

            result = data.get("result", {})
            reviews = result.get("reviews", [])

            return {
                "name": result.get("name", ""),
                "address": result.get("formatted_address", ""),
                "phone": result.get("formatted_phone_number", ""),
                "international_phone": result.get("international_phone_number", ""),
                "website": result.get("website", ""),
                "rating": result.get("rating", 0),
                "total_reviews": result.get("user_ratings_total", 0),
                "business_status": result.get("business_status", ""),
                "google_maps_url": result.get("url", ""),
                "opening_hours": result.get("opening_hours", {}).get("weekday_text", []),
                "is_open": result.get("opening_hours", {}).get("open_now"),
                "reviews": [
                    {
                        "author": r.get("author_name", ""),
                        "rating": r.get("rating", 0),
                        "text": r.get("text", ""),
                        "time_ago": r.get("relative_time_description", ""),
                    }
                    for r in reviews[:5]  # Top 5 reviews
                ],
            }

    except Exception as e:
        logger.error(f"Place details error: {e}")
        return {"error": str(e)}


async def get_directions(
    origin: str, destination: str, mode: str = "driving"
) -> dict:
    """
    Get directions between two locations.
    
    Args:
        origin: Starting point (address or "lat,lng")
        destination: End point (address or "lat,lng")
        mode: "driving", "walking", "transit", "bicycling"
    """
    if not settings.google_maps_api_key:
        return {"error": "Google Maps API key not configured"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://maps.googleapis.com/maps/api/directions/json",
                params={
                    "origin": origin,
                    "destination": destination,
                    "mode": mode,
                    "key": settings.google_maps_api_key,
                },
                timeout=15.0,
            )
            data = response.json()

            if data.get("status") != "OK":
                return {"error": f"Directions error: {data.get('status')}"}

            route = data["routes"][0]["legs"][0]
            return {
                "distance": route["distance"]["text"],
                "duration": route["duration"]["text"],
                "start_address": route["start_address"],
                "end_address": route["end_address"],
                "steps": [
                    {
                        "instruction": step.get("html_instructions", ""),
                        "distance": step.get("distance", {}).get("text", ""),
                        "duration": step.get("duration", {}).get("text", ""),
                    }
                    for step in route.get("steps", [])[:10]
                ],
            }

    except Exception as e:
        logger.error(f"Directions error: {e}")
        return {"error": str(e)}
