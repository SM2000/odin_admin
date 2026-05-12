import os
import requests

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")


def _fetch_pexels(query: str, count: int) -> list[dict]:
    if not PEXELS_API_KEY:
        return []
    resp = requests.get(
        "https://api.pexels.com/v1/search",
        headers={"Authorization": PEXELS_API_KEY},
        params={"query": query, "per_page": count, "orientation": "landscape"},
        timeout=10,
    )
    if not resp.ok:
        return []
    photos = resp.json().get("photos", [])
    return [
        {
            "url": p["src"]["large"],
            "alt": p.get("alt") or query,
            "source": "Pexels",
            "photographer": p.get("photographer", ""),
        }
        for p in photos
    ]


def _fetch_unsplash(query: str, count: int) -> list[dict]:
    if not UNSPLASH_ACCESS_KEY:
        return []
    resp = requests.get(
        "https://api.unsplash.com/search/photos",
        params={
            "query": query,
            "per_page": count,
            "orientation": "landscape",
            "client_id": UNSPLASH_ACCESS_KEY,
        },
        timeout=10,
    )
    if not resp.ok:
        return []
    results = resp.json().get("results", [])
    return [
        {
            "url": r["urls"]["regular"],
            "alt": r.get("alt_description") or query,
            "source": "Unsplash",
            "photographer": r.get("user", {}).get("name", ""),
        }
        for r in results
    ]


def fetch_images(query: str, count: int = 4) -> list[dict]:
    half = max(1, count // 2)
    images = _fetch_pexels(query, half) + _fetch_unsplash(query, count - half)
    # Pad from either source if the other failed
    if len(images) < count:
        images += _fetch_pexels(query, count - len(images))
    if len(images) < count:
        images += _fetch_unsplash(query, count - len(images))
    return images[:count]
