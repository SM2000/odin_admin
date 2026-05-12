import os
import requests

STORE_URL = os.getenv("SHOPIFY_STORE_URL", "")       # e.g. toosteppin.myshopify.com
ADMIN_TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN", "")   # shpat_...
BLOG_ID = os.getenv("SHOPIFY_BLOG_ID", "")
API_VERSION = "2025-01"


def _headers() -> dict:
    return {
        "X-Shopify-Access-Token": ADMIN_TOKEN,
        "Content-Type": "application/json",
    }


def _base_url() -> str:
    return f"https://{STORE_URL}/admin/api/{API_VERSION}"


def get_blogs() -> list[dict]:
    """Return all blogs on the store so the user can pick one."""
    resp = requests.get(f"{_base_url()}/blogs.json", headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json().get("blogs", [])


def publish_article(
    title: str,
    body_html: str,
    tags: list[str],
    meta_description: str,
    blog_id: str | None = None,
    published: bool = True,
) -> dict:
    """Create an article on the Shopify blog. Returns the created article dict."""
    bid = blog_id or BLOG_ID
    if not bid:
        raise ValueError("No SHOPIFY_BLOG_ID configured.")

    payload = {
        "article": {
            "title": title,
            "body_html": body_html,
            "tags": ", ".join(tags),
            "metafields": [
                {
                    "key": "description_tag",
                    "value": meta_description,
                    "type": "single_line_text_field",
                    "namespace": "global",
                }
            ],
            "published": published,
        }
    }

    resp = requests.post(
        f"{_base_url()}/blogs/{bid}/articles.json",
        headers=_headers(),
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("article", {})
