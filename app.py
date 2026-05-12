import os
import requests
import streamlit as st
from dotenv import load_dotenv, dotenv_values

load_dotenv()

from lib.claude_ad_writer import generate_ad_variations
from lib.image_fetcher import fetch_images
from lib.ad_previewer import render_facebook_preview
from lib.buffer_publisher import get_profiles, post_update

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")

st.set_page_config(
    page_title="HuntWithOdin · Ad Creator",
    page_icon="🦌",
    layout="wide",
)

# ── Sidebar navigation ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🦌 HuntWithOdin\n### Ad Creator")
    st.divider()
    page = st.radio("Navigation", ["Create Ads", "API Settings"], label_visibility="collapsed")
    st.divider()
    st.caption("Powered by Claude · Anthropic")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: API SETTINGS
# ══════════════════════════════════════════════════════════════════════════════
if page == "API Settings":
    st.title("API Settings")
    st.markdown(
        "Keys are saved to a local `.env` file on this machine and are never "
        "transmitted anywhere other than the respective services."
    )

    current = dotenv_values(ENV_PATH) if os.path.exists(ENV_PATH) else {}

    def _get(key: str) -> str:
        return current.get(key) or os.getenv(key) or ""

    st.subheader("Claude (Anthropic)")
    anthropic_key = st.text_input(
        "ANTHROPIC_API_KEY", value=_get("ANTHROPIC_API_KEY"), type="password",
        help="console.anthropic.com",
    )

    st.subheader("Images")
    col1, col2 = st.columns(2)
    with col1:
        pexels_key = st.text_input(
            "PEXELS_API_KEY", value=_get("PEXELS_API_KEY"), type="password",
            help="pexels.com/api — free",
        )
    with col2:
        unsplash_key = st.text_input(
            "UNSPLASH_ACCESS_KEY", value=_get("UNSPLASH_ACCESS_KEY"), type="password",
            help="unsplash.com/developers — free",
        )

    st.subheader("Buffer")
    buffer_token = st.text_input(
        "BUFFER_ACCESS_TOKEN", value=_get("BUFFER_ACCESS_TOKEN"), type="password",
        help="buffer.com/developers/apps — create an app and copy the Access Token",
    )

    if st.button("💾 Save Settings", type="primary"):
        lines = [
            f"ANTHROPIC_API_KEY={anthropic_key}",
            f"PEXELS_API_KEY={pexels_key}",
            f"UNSPLASH_ACCESS_KEY={unsplash_key}",
            f"BUFFER_ACCESS_TOKEN={buffer_token}",
        ]
        with open(ENV_PATH, "w") as f:
            f.write("\n".join(lines) + "\n")
        for line in lines:
            k, _, v = line.partition("=")
            if v:
                os.environ[k] = v
        st.success("Settings saved and active for this session.")

    st.divider()
    st.subheader("Test connections")
    tcol1, tcol2, tcol3 = st.columns(3)

    with tcol1:
        if st.button("Test Claude"):
            key = os.getenv("ANTHROPIC_API_KEY") or anthropic_key
            if not key:
                st.error("No key.")
            else:
                try:
                    import anthropic
                    c = anthropic.Anthropic(api_key=key)
                    c.messages.create(
                        model="claude-haiku-4-5-20251001", max_tokens=5,
                        messages=[{"role": "user", "content": "Hi"}],
                    )
                    st.success("Claude ✓")
                except Exception as e:
                    st.error(str(e))

    with tcol2:
        if st.button("Test Pexels"):
            key = os.getenv("PEXELS_API_KEY") or pexels_key
            if not key:
                st.error("No key.")
            else:
                r = requests.get(
                    "https://api.pexels.com/v1/search",
                    headers={"Authorization": key},
                    params={"query": "hunting", "per_page": 1},
                    timeout=8,
                )
                st.success("Pexels ✓") if r.ok else st.error(f"{r.status_code}")

    with tcol3:
        if st.button("Test Buffer"):
            token = os.getenv("BUFFER_ACCESS_TOKEN") or buffer_token
            if not token:
                st.error("No token.")
            else:
                r = requests.get(
                    "https://api.bufferapp.com/1/profiles.json",
                    params={"access_token": token},
                    timeout=8,
                )
                if r.ok:
                    profiles = [p for p in r.json() if p.get("service") in ("facebook", "instagram")]
                    st.success(f"Buffer ✓  ({len(profiles)} FB/IG profile(s))")
                else:
                    st.error(f"{r.status_code}: {r.text[:120]}")

    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: CREATE ADS
# ══════════════════════════════════════════════════════════════════════════════
if not os.getenv("ANTHROPIC_API_KEY"):
    st.warning("⚠️ Anthropic API key not set — go to **API Settings**.", icon="🔑")

st.title("HuntWithOdin · Ad Creator")
st.markdown("Describe your campaign and Claude will write three scroll-stopping ad variations.")

# ── Campaign inputs ───────────────────────────────────────────────────────────
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
    num_images = st.slider("Images per variation", 1, 4, 2)
    submitted = st.form_submit_button("✨ Generate Ad Variations", type="primary", use_container_width=True)

# ── Session state ─────────────────────────────────────────────────────────────
for key in ("variations", "images_by_variation", "selected_variation"):
    if key not in st.session_state:
        st.session_state[key] = None if key == "selected_variation" else []

# ── Generation ────────────────────────────────────────────────────────────────
if submitted:
    if not os.getenv("ANTHROPIC_API_KEY"):
        st.error("Set your Anthropic API key in API Settings first.")
        st.stop()

    with st.spinner("Claude is writing your ad variations…"):
        try:
            variations = generate_ad_variations(goal, audience, ad_format, angle_notes, platform)
            st.session_state.variations = variations
            st.session_state.images_by_variation = []
            st.session_state.selected_variation = None
        except Exception as e:
            st.error(f"Generation failed: {e}")
            st.stop()

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

                # Assemble the post text (what actually goes into Buffer)
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
    elif not os.getenv("BUFFER_ACCESS_TOKEN"):
        st.warning("Add your Buffer access token in **API Settings**.")
    else:
        st.markdown(f"**Publishing:** Variation {selected['index']+1}")

        try:
            profiles = get_profiles()
        except Exception as e:
            st.error(f"Could not load Buffer profiles: {e}")
            profiles = []

        if not profiles:
            st.warning("No Facebook or Instagram profiles found in your Buffer account.")
        else:
            profile_options = {
                f"{p.get('service','').title()} · {p.get('formatted_username', p.get('id',''))}": p["id"]
                for p in profiles
            }
            chosen_profiles = st.multiselect(
                "Post to", options=list(profile_options.keys()),
                default=list(profile_options.keys()),
            )
            selected_profile_ids = [profile_options[k] for k in chosen_profiles]

            # Image selection for publish
            pub_img_url = None
            if selected["images"]:
                pub_img_labels = [f"Image {j+1} ({img['source']})" for j, img in enumerate(selected["images"])]
                pub_img_choice = st.radio("Image to attach", pub_img_labels, key="pub_img")
                pub_img_idx = pub_img_labels.index(pub_img_choice)
                pub_img_url = selected["images"][pub_img_idx]["url"]

            post_now = st.checkbox("Post immediately (skip queue)", value=False)
            scheduled_at = None
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
