import os
import requests

GRAPHQL_ENDPOINT = "https://api.buffer.com/graphql"


def _headers() -> dict:
    token = os.getenv("BUFFER_ACCESS_TOKEN", "")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _gql(query: str, variables: dict | None = None) -> dict:
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = requests.post(GRAPHQL_ENDPOINT, headers=_headers(), json=payload, timeout=15)
    # Surface the actual API error body, not just the HTTP status
    if not resp.ok:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:400]}")
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(data["errors"][0]["message"])
    return data.get("data", {})


def _get_org_id() -> str:
    data = _gql("query { account { organizations { id } } }")
    orgs = data.get("account", {}).get("organizations", [])
    if not orgs:
        raise RuntimeError("No Buffer organizations found on this account.")
    return orgs[0]["id"]


def get_channels() -> list[dict]:
    org_id = _get_org_id()
    data = _gql(
        """
        query GetChannels($input: ChannelsInput!) {
          channels(input: $input) {
            id
            name
            service
          }
        }
        """,
        {"input": {"organizationId": org_id}},
    )
    channels = data.get("channels", [])
    return [c for c in channels if c.get("service") in ("facebook", "instagram")]


def get_profiles() -> list[dict]:
    return get_channels()


def post_update(
    profile_ids: list[str],
    text: str,
    image_url: str | None = None,
    scheduled_at: str | None = None,
    now: bool = False,
) -> dict:
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

        data = _gql(mutation, variables)
        payload = data.get("createPost", {})
        if payload.get("errors"):
            raise RuntimeError(payload["errors"][0]["message"])
        results.append(payload.get("post", {}))

    return {"posts": results}
