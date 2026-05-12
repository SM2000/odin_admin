import os
import requests

GRAPHQL_ENDPOINT = "https://api.buffer.com/graphql"


def _headers() -> dict:
    token = os.getenv("BUFFER_ACCESS_TOKEN", "")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def get_channels() -> list[dict]:
    query = """
    query GetChannels {
      channels {
        id
        name
        service
        serviceType
        avatar
      }
    }
    """
    resp = requests.post(
        GRAPHQL_ENDPOINT,
        headers=_headers(),
        json={"query": query},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(data["errors"][0]["message"])
    channels = data.get("data", {}).get("channels", [])
    return [c for c in channels if c.get("service") in ("facebook", "instagram")]


# Keep old name so app.py import doesn't break
def get_profiles() -> list[dict]:
    return get_channels()


def post_update(
    profile_ids: list[str],
    text: str,
    image_url: str | None = None,
    scheduled_at: str | None = None,
    now: bool = False,
) -> dict:
    """Post or queue an update to each channel via the Buffer GraphQL API."""
    mutation = """
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        post {
          id
          status
          text
        }
        errors {
          message
        }
      }
    }
    """

    mode = "SHARE_NOW" if now else "QUEUE"
    results = []

    assets = []
    if image_url:
        assets = [{"image": {"url": image_url, "thumbnailUrl": image_url}}]

    for channel_id in profile_ids:
        variables: dict = {
            "input": {
                "channelId": channel_id,
                "text": text,
                "schedulingType": mode,
            }
        }
        if assets:
            variables["input"]["assets"] = assets
        if scheduled_at and not now:
            variables["input"]["scheduledAt"] = scheduled_at

        resp = requests.post(
            GRAPHQL_ENDPOINT,
            headers=_headers(),
            json={"query": mutation, "variables": variables},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            raise RuntimeError(data["errors"][0]["message"])
        payload = data.get("data", {}).get("createPost", {})
        if payload.get("errors"):
            raise RuntimeError(payload["errors"][0]["message"])
        results.append(payload.get("post", {}))

    return {"posts": results}
