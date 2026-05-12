import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from lib.claude_ad_writer import generate_ad_variations
from lib.image_fetcher import fetch_images
from lib.ad_previewer import render_facebook_preview
from lib.buffer_publisher import get_profiles, post_update

st.set_page_config(
    page_title="HuntWithOdin · Ad Creator",
    page_icon="🦌",
    layout="wide",
)

with st.sidebar:
    st.markdown("## 🦌 HuntWithOdin\n### Ad Creator")
    st.divider()
    st.caption("Powered by Claude · Anthropic")

# ── Campaign inputs ───────────────────────────────────────────────────────────
st.title("HuntWithOdin · Ad Creator")
st.markdown("Describe your campaign and Claude will write three scroll-stopping ad variations.")

with st.form("campaign_form"):
    c1, c2, c3 = st.columns(3)
    with c1:
        goal = st.selectbox(
            "Campaign goal",
            ["App Downloads", "Free Trial Sign-ups", "Paid Subscription", "Brand Awareness", "Website Traffic"],
        )
    with c2:
        platform = st.selectbox(
            "Platform",
            ["Facebook", "Instagram", "Both (Facebook + Instagram)"],
        )
    with c3:
        ad_format = st.selectbox(
            "Ad format",
            ["Facebook Feed", "Instagram Feed", "Facebook Story", "Instagram Story", "Carousel"],
        )

    audience = st.selectbox(
        "Primary audience",
        [
            "Elk hunters — Western states",
            "Mule deer hunters — Western states",
            "Whitetail deer hunters — Nationwide",
            "Turkey hunters — Spring season",
            "Pronghorn / antelope hunters",
            "Bear hunters",
            "Multi-species / general hunters",
            "New hunters / beginners",
            "DIY public land hunters",
        ],
    )
    angle_notes = st.text_input(
        "Additional notes / angle (optional)",
        placeholder="e.g. 'focus on the tag draw success rate', 'mention it's free to start', 'use urgency around elk season opening'",
    )
    has_image_keys = bool(os.getenv("PEXELS_API_KEY") or os.getenv("UNSPLASH_ACCESS_KEY"))
    num_images = st.slider("Images per variation", 1, 4, 2) if has_image_keys else 0
    submitted = st.form_submit_button("✨ Generate Ad Variations", type="primary", use_container_width=True)

# ── Session state ─────────────────────────────────────────────────────────────
for key in ("variations", "images_by_variation", "selected_variation"):
    if key not in st.session_state:
        st.session_state[key] = None if key == "selected_variation" else []

# ── Generation ────────────────────────────────────────────────────────────────
if submitted:
    with st.spinner("Claude is writing your ad variations…"):
        try:
            variations = generate_ad_variations(goal, audience, ad_format, angle_notes, platform)
            st.session_state.variations = variations
            st.session_state.images_by_variation = []
            st.session_state.selected_variation = None
        except Exception as e:
            st.error(f"Generation failed: {e}")
            st.stop()

    if num_images > 0:
        with st.spinner("Fetching hunting images…"):
            images_by_variation = []
            for v in variations:
                query = v.get("image_search_query", "hunting outdoor wildlife")
                imgs = fetch_images(query, num_images)
                images_by_variation.append(imgs)
            st.session_state.images_by_variation = images_by_variation

    st.success(f"Generated {len(variations)} ad variations!")

# ── Display variations ────────────────────────────────────────────────────────
if st.session_state.variations:
    variations = st.session_state.variations
    images_by_variation = st.session_state.images_by_variation

    st.divider()
    st.subheader("Ad Variations")

    tabs = st.tabs([f"Variation {i+1} · {v.get('angle','')}" for i, v in enumerate(variations)])

    for i, (tab, variation) in enumerate(zip(tabs, variations)):
        imgs = images_by_variation[i] if i < len(images_by_variation) else []

        with tab:
            col_preview, col_copy = st.columns([1, 1])

            with col_copy:
                st.markdown(f"**Angle:** {variation.get('angle','')}")
                st.markdown(f"**Hook:** *{variation.get('hook','')}*")
                st.divider()

                primary = st.text_area(
                    "Primary text",
                    value=variation.get("primary_text", ""),
                    height=140,
                    key=f"primary_{i}",
                )
                headline = st.text_input("Headline", value=variation.get("headline", ""), key=f"headline_{i}")
                description = st.text_input("Description", value=variation.get("description", ""), key=f"desc_{i}")
                cta = st.selectbox(
                    "CTA button",
                    ["Learn More", "Download", "Sign Up", "Get Started", "Try Free", "Shop Now"],
                    index=["Learn More", "Download", "Sign Up", "Get Started", "Try Free", "Shop Now"].index(
                        variation.get("cta", "Learn More")
                    ) if variation.get("cta") in ["Learn More", "Download", "Sign Up", "Get Started", "Try Free", "Shop Now"] else 0,
                    key=f"cta_{i}",
                )

                post_text = f"{primary}\n\n👉 {headline}\n\nhuntwithOdin.com"

                if st.button(f"Select Variation {i+1} for Publishing", key=f"select_{i}", type="secondary"):
                    st.session_state.selected_variation = {
                        "index": i,
                        "primary_text": primary,
                        "headline": headline,
                        "description": description,
                        "cta": cta,
                        "post_text": post_text,
                        "images": imgs,
                    }
                    st.success(f"Variation {i+1} selected. Scroll down to publish.")

            with col_preview:
                st.markdown("**Preview**")
                selected_img_url = None
                if imgs:
                    img_labels = [f"Image {j+1} ({img['source']})" for j, img in enumerate(imgs)]
                    chosen = st.radio("Choose image", img_labels, key=f"img_radio_{i}")
                    img_idx = img_labels.index(chosen)
                    selected_img_url = imgs[img_idx]["url"]
                    st.image(selected_img_url, use_container_width=True)

                preview_variation = {
                    "primary_text": st.session_state.get(f"primary_{i}", variation.get("primary_text", "")),
                    "headline": st.session_state.get(f"headline_{i}", variation.get("headline", "")),
                    "description": st.session_state.get(f"desc_{i}", variation.get("description", "")),
                    "cta": st.session_state.get(f"cta_{i}", variation.get("cta", "Learn More")),
                }
                html_preview = render_facebook_preview(preview_variation, selected_img_url, platform)
                st.markdown("**Ad card mockup**")
                st.components.v1.html(html_preview, height=560, scrolling=False)

    # ── Publish panel ─────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Publish via Buffer")

    selected = st.session_state.selected_variation
    if not selected:
        st.info("Select a variation above to publish it.")
    else:
        st.markdown(f"**Publishing:** Variation {selected['index']+1}")

        try:
            profiles = get_profiles()
        except Exception as e:
            st.error(f"Could not load Buffer channels: {e}")
            profiles = []

        if not profiles:
            st.warning("No Facebook or Instagram channels found in your Buffer account.")
        else:
            profile_options = {
                f"{p.get('service','').title()} · {p.get('name', p.get('id',''))}": p["id"]
                for p in profiles
            }
            chosen_profiles = st.multiselect(
                "Post to", options=list(profile_options.keys()),
                default=list(profile_options.keys()),
            )
            selected_profile_ids = [profile_options[k] for k in chosen_profiles]

            pub_img_url = None
            if selected["images"]:
                pub_img_labels = [f"Image {j+1} ({img['source']})" for j, img in enumerate(selected["images"])]
                pub_img_choice = st.radio("Image to attach", pub_img_labels, key="pub_img")
                pub_img_idx = pub_img_labels.index(pub_img_choice)
                pub_img_url = selected["images"][pub_img_idx]["url"]

            post_now = st.checkbox("Post immediately (skip queue)", value=False)
            if not post_now:
                st.caption("The post will be added to your Buffer queue at its next scheduled slot.")

            with st.expander("Preview post text"):
                st.text(selected["post_text"])

            if st.button("🚀 Send to Buffer", type="primary") and selected_profile_ids:
                with st.spinner("Sending to Buffer…"):
                    try:
                        result = post_update(
                            profile_ids=selected_profile_ids,
                            text=selected["post_text"],
                            image_url=pub_img_url,
                            now=post_now,
                        )
                        st.success("Posted to Buffer successfully!")
                        st.json(result)
                    except Exception as e:
                        st.error(f"Buffer post failed: {e}")
