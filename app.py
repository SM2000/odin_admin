import os
import re
import streamlit as st
from dotenv import load_dotenv, dotenv_values

load_dotenv()

from lib.claude_writer import generate_blog_post
from lib.image_fetcher import fetch_images
from lib.html_builder import build_html
from lib.shopify_publisher import get_blogs, publish_article

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")

st.set_page_config(
    page_title="TooSteppin Blog Generator",
    page_icon="👟",
    layout="wide",
)

# ── Sidebar navigation ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 👟 TooSteppin")
    page = st.radio("Navigation", ["Blog Generator", "API Settings"], label_visibility="collapsed")
    st.divider()
    if page == "Blog Generator":
        tone = st.selectbox(
            "Writing tone",
            ["Conversational & Friendly", "Authoritative & Expert", "Playful & Energetic", "Inspirational"],
        )
        word_count = st.slider("Target word count", 400, 1200, 700, step=100)
        num_images = st.slider("Number of images", 1, 6, 3)
    st.divider()
    st.caption("Powered by Claude · Anthropic")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: API SETTINGS
# ══════════════════════════════════════════════════════════════════════════════
if page == "API Settings":
    st.title("API Settings")
    st.markdown(
        "Enter your API keys below. They are saved to a local `.env` file on this machine "
        "and are never sent anywhere other than the respective services."
    )

    current = dotenv_values(ENV_PATH) if os.path.exists(ENV_PATH) else {}

    def _get(key: str) -> str:
        return current.get(key) or os.getenv(key) or ""

    st.subheader("Claude (Anthropic)")
    anthropic_key = st.text_input(
        "ANTHROPIC_API_KEY",
        value=_get("ANTHROPIC_API_KEY"),
        type="password",
        help="Get yours at console.anthropic.com",
    )

    st.subheader("Images")
    col1, col2 = st.columns(2)
    with col1:
        pexels_key = st.text_input(
            "PEXELS_API_KEY",
            value=_get("PEXELS_API_KEY"),
            type="password",
            help="Free at pexels.com/api",
        )
    with col2:
        unsplash_key = st.text_input(
            "UNSPLASH_ACCESS_KEY",
            value=_get("UNSPLASH_ACCESS_KEY"),
            type="password",
            help="Free at unsplash.com/developers",
        )

    st.subheader("Shopify")
    col3, col4 = st.columns(2)
    with col3:
        shopify_url = st.text_input(
            "SHOPIFY_STORE_URL",
            value=_get("SHOPIFY_STORE_URL"),
            placeholder="toosteppin.myshopify.com",
            help="Your .myshopify.com URL (no https://)",
        )
    with col4:
        shopify_token = st.text_input(
            "SHOPIFY_ADMIN_TOKEN",
            value=_get("SHOPIFY_ADMIN_TOKEN"),
            type="password",
            help="Shopify Admin → Settings → Apps → Custom app token",
        )
    shopify_blog_id = st.text_input(
        "SHOPIFY_BLOG_ID (optional)",
        value=_get("SHOPIFY_BLOG_ID"),
        help="Leave blank — the Blog Generator page will let you pick from a dropdown once your token is saved.",
    )

    if st.button("💾 Save Settings", type="primary"):
        lines = [
            f"ANTHROPIC_API_KEY={anthropic_key}",
            f"PEXELS_API_KEY={pexels_key}",
            f"UNSPLASH_ACCESS_KEY={unsplash_key}",
            f"SHOPIFY_STORE_URL={shopify_url}",
            f"SHOPIFY_ADMIN_TOKEN={shopify_token}",
            f"SHOPIFY_BLOG_ID={shopify_blog_id}",
        ]
        with open(ENV_PATH, "w") as f:
            f.write("\n".join(lines) + "\n")
        # Hot-reload into os.environ for the current session
        for line in lines:
            k, _, v = line.partition("=")
            if v:
                os.environ[k] = v
        st.success("Settings saved. Your keys are active for this session.")
        st.info("If you restart the app, they will be loaded automatically from the .env file.")

    # Connection test buttons
    st.divider()
    st.subheader("Test connections")
    tcol1, tcol2, tcol3 = st.columns(3)

    with tcol1:
        if st.button("Test Claude"):
            key = os.getenv("ANTHROPIC_API_KEY") or anthropic_key
            if not key:
                st.error("No API key entered.")
            else:
                try:
                    import anthropic
                    c = anthropic.Anthropic(api_key=key)
                    c.messages.create(
                        model="claude-haiku-4-5-20251001",
                        max_tokens=10,
                        messages=[{"role": "user", "content": "Hi"}],
                    )
                    st.success("Claude ✓")
                except Exception as e:
                    st.error(f"Failed: {e}")

    with tcol2:
        if st.button("Test Pexels"):
            key = os.getenv("PEXELS_API_KEY") or pexels_key
            if not key:
                st.error("No API key entered.")
            else:
                import requests
                r = requests.get(
                    "https://api.pexels.com/v1/search",
                    headers={"Authorization": key},
                    params={"query": "dance", "per_page": 1},
                    timeout=8,
                )
                if r.ok:
                    st.success("Pexels ✓")
                else:
                    st.error(f"Failed: {r.status_code}")

    with tcol3:
        if st.button("Test Shopify"):
            url = os.getenv("SHOPIFY_STORE_URL") or shopify_url
            token = os.getenv("SHOPIFY_ADMIN_TOKEN") or shopify_token
            if not url or not token:
                st.error("Store URL and token required.")
            else:
                import requests
                r = requests.get(
                    f"https://{url}/admin/api/2025-01/blogs.json",
                    headers={"X-Shopify-Access-Token": token},
                    timeout=8,
                )
                if r.ok:
                    blogs = r.json().get("blogs", [])
                    st.success(f"Shopify ✓  ({len(blogs)} blog(s) found)")
                else:
                    st.error(f"Failed: {r.status_code}")

    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: BLOG GENERATOR
# ══════════════════════════════════════════════════════════════════════════════
missing_keys = [k for k in ("ANTHROPIC_API_KEY",) if not os.getenv(k)]
if missing_keys:
    st.warning(
        "⚠️ Some API keys are not configured. Go to **API Settings** in the sidebar to add them.",
        icon="🔑",
    )

st.title("TooSteppin Blog Generator")
st.markdown("Turn a topic idea into a publish-ready blog post in seconds.")

col1, col2 = st.columns([2, 1])
with col1:
    topic = st.text_area(
        "Blog topic / idea",
        placeholder="e.g. 'How to choose the right dance shoes for Latin ballroom'",
        height=100,
    )
with col2:
    keywords_raw = st.text_area(
        "SEO keywords (one per line)",
        placeholder="dance shoes\nLatin ballroom\ndance footwear",
        height=100,
    )

generate_btn = st.button("✨ Generate Blog Post", type="primary", use_container_width=True)

if "blog" not in st.session_state:
    st.session_state.blog = None
if "images" not in st.session_state:
    st.session_state.images = []
if "html" not in st.session_state:
    st.session_state.html = ""

if generate_btn:
    if not topic.strip():
        st.error("Please enter a blog topic.")
        st.stop()
    if not os.getenv("ANTHROPIC_API_KEY"):
        st.error("Anthropic API key is not set. Go to API Settings first.")
        st.stop()

    keywords = [k.strip() for k in keywords_raw.splitlines() if k.strip()]

    with st.spinner("Claude is writing your blog post…"):
        try:
            blog = generate_blog_post(topic, keywords, tone, word_count)
            st.session_state.blog = blog
        except Exception as e:
            st.error(f"Blog generation failed: {e}")
            st.stop()

    with st.spinner("Fetching images…"):
        query = blog.get("image_search_query", topic)
        images = fetch_images(query, num_images)
        st.session_state.images = images

    st.session_state.html = build_html(blog, images)
    st.success("Blog post ready!")

if st.session_state.blog:
    blog = st.session_state.blog
    html = st.session_state.html
    images = st.session_state.images

    st.divider()

    title = st.text_input("Title", value=blog.get("title", ""))
    meta = st.text_input(
        "Meta description",
        value=blog.get("meta_description", ""),
        help="Shown in Google search results (aim for 150–160 characters)",
    )
    tags_raw = st.text_input(
        "Tags (comma-separated)",
        value=", ".join(blog.get("tags", [])),
    )

    tab_preview, tab_html, tab_images = st.tabs(["Preview", "HTML", "Images"])

    with tab_preview:
        st.markdown("---")
        st.markdown(f"## {title}")
        for img in images:
            st.image(img["url"], caption=img["alt"], use_container_width=True)
        preview_text = re.sub(r"<[^>]+>", " ", html).strip()
        st.markdown(preview_text)

    with tab_html:
        st.code(html, language="html")

    with tab_images:
        if images:
            cols = st.columns(min(len(images), 3))
            for i, img in enumerate(images):
                with cols[i % 3]:
                    st.image(img["url"], caption=f"{img['source']} · {img['photographer']}", use_container_width=True)
        else:
            st.info("No images fetched. Add Pexels / Unsplash keys in API Settings.")

    st.divider()
    st.subheader("Publish to Shopify")

    shopify_ok = all([os.getenv("SHOPIFY_STORE_URL"), os.getenv("SHOPIFY_ADMIN_TOKEN")])

    if not shopify_ok:
        st.info("Add your Shopify credentials in **API Settings** to enable one-click publishing.")
    else:
        publish_as_draft = st.checkbox("Save as draft (don't publish immediately)", value=False)
        blog_id_override = None
        try:
            blogs = get_blogs()
            if blogs:
                blog_options = {b["title"]: str(b["id"]) for b in blogs}
                selected_blog = st.selectbox("Publish to blog", options=list(blog_options.keys()))
                blog_id_override = blog_options[selected_blog]
        except Exception:
            st.info("Could not fetch blogs — will use SHOPIFY_BLOG_ID from settings.")

        if st.button("🚀 Publish to Shopify", type="primary"):
            tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()]
            with st.spinner("Publishing…"):
                try:
                    article = publish_article(
                        title=title,
                        body_html=html,
                        tags=tags_list,
                        meta_description=meta,
                        blog_id=blog_id_override,
                        published=not publish_as_draft,
                    )
                    article_id = article.get("id")
                    store = os.getenv("SHOPIFY_STORE_URL", "")
                    st.success(f"Published! Article ID: {article_id}")
                    if store and article_id:
                        st.markdown(f"[View in Shopify Admin](https://{store}/admin/articles/{article_id})")
                except Exception as e:
                    st.error(f"Publish failed: {e}")
