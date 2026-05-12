import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from lib.claude_writer import generate_blog_post
from lib.image_fetcher import fetch_images
from lib.html_builder import build_html
from lib.shopify_publisher import get_blogs, publish_article

st.set_page_config(
    page_title="TooSteppin Blog Generator",
    page_icon="👟",
    layout="wide",
)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://cdn.shopify.com/s/files/1/0000/0000/files/toosteppin-logo.png",
        use_container_width=True,
        caption="",
    )
    st.title("Settings")

    tone = st.selectbox(
        "Writing tone",
        ["Conversational & Friendly", "Authoritative & Expert", "Playful & Energetic", "Inspirational"],
    )
    word_count = st.slider("Target word count", 400, 1200, 700, step=100)
    num_images = st.slider("Number of images", 1, 6, 3)

    st.divider()
    st.caption("TooSteppin Blog Generator · Powered by Claude")

# ── Main ─────────────────────────────────────────────────────────────────────
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

# ── Session state ─────────────────────────────────────────────────────────────
if "blog" not in st.session_state:
    st.session_state.blog = None
if "images" not in st.session_state:
    st.session_state.images = []
if "html" not in st.session_state:
    st.session_state.html = ""

# ── Generation ────────────────────────────────────────────────────────────────
if generate_btn:
    if not topic.strip():
        st.error("Please enter a blog topic.")
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

# ── Preview & Publish ─────────────────────────────────────────────────────────
if st.session_state.blog:
    blog = st.session_state.blog
    html = st.session_state.html
    images = st.session_state.images

    st.divider()

    # Editable title
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
        # Render the HTML as markdown-ish preview (images shown, HTML tags stripped for display)
        import re
        preview_text = re.sub(r"<[^>]+>", " ", html).strip()
        for img in images:
            st.image(img["url"], caption=img["alt"], use_container_width=True)
        st.markdown(preview_text)

    with tab_html:
        st.code(html, language="html")
        st.button(
            "📋 Copy HTML",
            on_click=lambda: st.write(
                f'<script>navigator.clipboard.writeText({repr(html)})</script>',
                unsafe_allow_html=True,
            ),
        )

    with tab_images:
        if images:
            cols = st.columns(min(len(images), 3))
            for i, img in enumerate(images):
                with cols[i % 3]:
                    st.image(img["url"], caption=f"{img['source']} · {img['photographer']}", use_container_width=True)
        else:
            st.info("No images were fetched. Check your Pexels / Unsplash API keys.")

    st.divider()
    st.subheader("Publish to Shopify")

    shopify_ok = all([
        os.getenv("SHOPIFY_STORE_URL"),
        os.getenv("SHOPIFY_ADMIN_TOKEN"),
    ])

    if not shopify_ok:
        st.warning("Shopify credentials not configured. Set SHOPIFY_STORE_URL and SHOPIFY_ADMIN_TOKEN in your .env file.")
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
            st.info("Could not fetch blogs — will use SHOPIFY_BLOG_ID from environment.")

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
                        st.markdown(
                            f"[View in Shopify Admin](https://{store}/admin/articles/{article_id})"
                        )
                except Exception as e:
                    st.error(f"Publish failed: {e}")
