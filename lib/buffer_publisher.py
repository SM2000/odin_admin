import os
import requests

BASE = "https://api.bufferapp.com/1"


def _token() -> str:
    return os.getenv("BUFFER_ACCESS_TOKEN", "")


def get_profiles() -> list[dict]:
    resp = requests.get(
        f"{BASE}/profiles.json",
        params={"access_token": _token()},
        timeout=10,
    )
    resp.raise_for_status()
    profiles = resp.json()
    # Return only Facebook and Instagram profiles
    return [
        p for p in profiles
        if p.get("service") in ("facebook", "instagram")
    ]


def post_update(
    profile_ids: list[str],
    text: str,
    image_url: str | None = None,
    scheduled_at: str | None = None,
    now: bool = False,
) -> dict:
    """
    Post or schedule an update via Buffer.
    scheduled_at: ISO 8601 string e.g. "2026-05-13T10:00:00Z"
    now=True posts immediately, bypassing the queue.
    """
    data: dict = {
        "access_token": _token(),
        "text": text,
        "now": "true" if now else "false",
    }
    for pid in profile_ids:
        data.setdefault("profile_ids[]", [])
        if isinstance(data["profile_ids[]"], list):
            data["profile_ids[]"].append(pid)

    if image_url:
        data["media[photo]"] = image_url
        data["media[thumbnail]"] = image_url

    if scheduled_at and not now:
        data["scheduled_at"] = scheduled_at

    resp = requests.post(
        f"{BASE}/updates/create.json",
        data=data,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()
