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


def get_scheduled_posts(channel_ids: list[str]) -> list[dict]:
    """Return upcoming scheduled posts across the given channels."""
    query = """
    query GetPosts($input: PostsInput!) {
      posts(input: $input) {
        edges {
          node {
            id
            text
            status
            dueAt
            channel {
              id
              name
              service
            }
          }
        }
      }
    }
    """
    results = []
    for channel_id in channel_ids:
        try:
            data = _gql(query, {"input": {"channelId": channel_id, "status": "scheduled"}})
            edges = data.get("posts", {}).get("edges", [])
            results.extend(edge["node"] for edge in edges if edge.get("node"))
        except Exception:
            # Skip channels that error — still show others
            continue
    # Sort by scheduledAt ascending
    results.sort(key=lambda p: p.get("dueAt") or "")
    return results


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
        __typename
        ... on PostActionSuccess {
          post {
            id
            status
            text
          }
        }
        ... on UnexpectedError { message }
        ... on InvalidInputError { message }
        ... on LimitReachedError { message }
        ... on UnauthorizedError { message }
        ... on NotFoundError { message }
      }
    }
    """
    if now:
        share_mode = "shareNow"
    elif scheduled_at:
        share_mode = "customScheduled"
    else:
        share_mode = "addToQueue"

    results = []
    for channel_id in profile_ids:
        variables: dict = {
            "input": {
                "channelId": channel_id,
                "text": text,
                "schedulingType": "automatic",
                "mode": share_mode,
                "assets": [{"image": {"url": image_url}}] if image_url else [],
            }
        }
        if scheduled_at:
            variables["input"]["dueAt"] = scheduled_at

        data = _gql(mutation, variables)
        payload = data.get("createPost", {})
        if payload.get("__typename") != "PostActionSuccess":
            msg = payload.get("message", payload.get("__typename", "unknown"))
            raise RuntimeError(f"Buffer error: {msg}")
        results.append(payload.get("post", {}))

    return {"posts": results}
