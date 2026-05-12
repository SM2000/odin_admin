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

st.title("HuntWithOdin · Ad Creator")
st.markdown("Select your formats and Claude will write three scroll-stopping variations for each.")

# ── Campaign form ─────────────────────────────────────────────────────────────
with st.form("campaign_form"):
    c1, c2 = st.columns(2)
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

    ad_formats = st.multiselect(
        "Ad formats",
        ["Facebook Feed", "Instagram Feed", "Facebook Story", "Instagram Story", "Carousel"],
        default=["Facebook Feed"],
        help="Claude generates 3 variations per format selected.",
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
        placeholder="e.g. 'focus on tag draw success rate', 'mention it's free to start'",
    )

    has_image_keys = bool(os.getenv("PEXELS_API_KEY") or os.getenv("UNSPLASH_ACCESS_KEY"))
    num_images = st.slider("Images to fetch per ad", 1, 4, 2) if has_image_keys else 0

    submitted = st.form_submit_button("✨ Generate Ads", type="primary", use_container_width=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "ads" not in st.session_state:
    st.session_state.ads = []

# ── Generation ────────────────────────────────────────────────────────────────
if submitted:
    if not ad_formats:
        st.error("Select at least one ad format.")
        st.stop()

    all_ads = []
    progress = st.progress(0, text="Starting…")

    for fi, fmt in enumerate(ad_formats):
        progress.progress(fi / len(ad_formats), text=f"Writing {fmt} variations…")
        try:
            variations = generate_ad_variations(goal, audience, fmt, angle_notes, platform)
        except Exception as e:
            st.error(f"Generation failed for {fmt}: {e}")
            st.stop()

        for v in variations:
            imgs = []
            if num_images > 0:
                imgs = fetch_images(v.get("image_search_query", "hunting outdoor wildlife"), num_images)
            all_ads.append({
                "format": fmt,
                "variation": v,
                "images": imgs,
            })

    progress.empty()
    st.session_state.ads = all_ads
    st.success(f"Generated {len(all_ads)} ads across {len(ad_formats)} format(s)!")

# ── Display ads ───────────────────────────────────────────────────────────────
if st.session_state.ads:
    ads = st.session_state.ads

    st.divider()
    st.subheader("Your Ads")

    tab_labels = [
        f"{ad['format']} · {ad['variation'].get('angle', f'V{i+1}')}"
        for i, ad in enumerate(ads)
    ]
    tabs = st.tabs(tab_labels)

    for i, (tab, ad) in enumerate(zip(tabs, ads)):
        variation = ad["variation"]
        imgs = ad["images"]

        with tab:
            col_copy, col_preview = st.columns([1, 1])

            with col_copy:
                st.markdown(f"**Format:** {ad['format']}")
                st.markdown(f"**Hook:** *{variation.get('hook', '')}*")
                st.divider()

                primary = st.text_area(
                    "Primary text", value=variation.get("primary_text", ""),
                    height=140, key=f"primary_{i}",
                )
                headline = st.text_input(
                    "Headline", value=variation.get("headline", ""), key=f"headline_{i}",
                )
                description = st.text_input(
                    "Description", value=variation.get("description", ""), key=f"desc_{i}",
                )
                ctas = ["Learn More", "Download", "Sign Up", "Get Started", "Try Free", "Shop Now"]
                cta = st.selectbox(
                    "CTA button", ctas,
                    index=ctas.index(variation.get("cta", "Learn More"))
                    if variation.get("cta") in ctas else 0,
                    key=f"cta_{i}",
                )

            with col_preview:
                # ── Image picker ──────────────────────────────────────────────
                selected_img_url = None

                if imgs:
                    st.markdown("**Fetched images**")
                    img_labels = [f"Image {j+1} · {img['source']}" for j, img in enumerate(imgs)]
                    img_choice = st.radio(
                        "Select image", img_labels,
                        key=f"img_radio_{i}",
                        label_visibility="collapsed",
                    )
                    img_idx = img_labels.index(img_choice)
                    selected_img_url = imgs[img_idx]["url"]
                    st.image(selected_img_url, use_container_width=True)

                st.markdown("**Upload your own**")
                uploaded = st.file_uploader(
                    "Replace with your image", type=["jpg", "jpeg", "png", "webp"],
                    key=f"upload_{i}", label_visibility="collapsed",
                )
                if uploaded:
                    st.image(uploaded, use_container_width=True)
                    selected_img_url = None  # uploaded shows in preview; Buffer needs URL below

                custom_url = st.text_input(
                    "Or paste a public image URL",
                    value="", key=f"custom_url_{i}",
                    placeholder="https://…",
                )
                if custom_url:
                    selected_img_url = custom_url
                    if not uploaded:
                        st.image(custom_url, use_container_width=True)

                if uploaded and not custom_url:
                    st.caption("💡 Uploaded images need a public URL to post via Buffer. Paste one above.")

                # ── Ad mockup ─────────────────────────────────────────────────
                st.divider()
                st.markdown("**Ad mockup**")
                preview_var = {
                    "primary_text": primary,
                    "headline": headline,
                    "description": description,
                    "cta": cta,
                }
                preview_url = custom_url or (selected_img_url if not uploaded else None)
                st.components.v1.html(
                    render_facebook_preview(preview_var, preview_url, platform),
                    height=520, scrolling=False,
                )

    # ── Publish panel ─────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Publish via Buffer")

    # Load channels once for the whole panel
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

        # ── Existing schedule viewer ──────────────────────────────────────────
        with st.expander("📅 View existing Buffer schedule", expanded=False):
            if st.button("Refresh schedule"):
                st.session_state.pop("buffer_schedule", None)

            if "buffer_schedule" not in st.session_state:
                with st.spinner("Fetching scheduled posts…"):
                    try:
                        all_ids = list(profile_options.values())
                        st.session_state.buffer_schedule = get_scheduled_posts(all_ids)
                    except Exception as e:
                        st.session_state.buffer_schedule = []
                        st.error(f"Could not load schedule: {e}")

            scheduled = st.session_state.get("buffer_schedule", [])
            if not scheduled:
                st.info("No scheduled posts found in your Buffer queue.")
            else:
                import pandas as pd
                rows = []
                for post in scheduled:
                    channel = post.get("channel", {})
                    raw_time = post.get("scheduledAt", "")
                    try:
                        from datetime import datetime, timezone
                        dt = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
                        formatted = dt.strftime("%b %d, %Y  %H:%M UTC")
                    except Exception:
                        formatted = raw_time
                    preview = (post.get("text") or "")[:80]
                    if len(post.get("text") or "") > 80:
                        preview += "…"
                    rows.append({
                        "Scheduled (UTC)": formatted,
                        "Channel": f"{channel.get('service','').title()} · {channel.get('name','')}",
                        "Post preview": preview,
                    })
                st.dataframe(
                    pd.DataFrame(rows),
                    use_container_width=True,
                    hide_index=True,
                )

        # ── Ad selection ──────────────────────────────────────────────────────
        st.markdown("**Select ads to publish:**")
        selected_indices = [
            i for i, ad in enumerate(ads)
            if st.checkbox(
                f"{ad['format']} · {ad['variation'].get('angle', f'V{i+1}')}",
                key=f"sel_{i}",
            )
        ]

        if selected_indices:
            chosen_profiles = st.multiselect(
                "Post to channels",
                options=list(profile_options.keys()),
                default=list(profile_options.keys()),
            )
            selected_profile_ids = [profile_options[k] for k in chosen_profiles]

            # ── Scheduling ────────────────────────────────────────────────────
            st.markdown("**When to post:**")
            timing = st.radio(
                "Timing",
                ["Add to queue (next available slot)", "Post immediately", "Schedule for specific date & time"],
                label_visibility="collapsed",
            )

            scheduled_at_iso = None
            if timing == "Schedule for specific date & time":
                from datetime import date, time, datetime, timezone
                dcol, tcol = st.columns(2)
                with dcol:
                    chosen_date = st.date_input("Date", value=date.today(), min_value=date.today())
                with tcol:
                    chosen_time = st.time_input("Time (UTC)", value=time(9, 0))
                scheduled_dt = datetime.combine(chosen_date, chosen_time, tzinfo=timezone.utc)
                scheduled_at_iso = scheduled_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                st.caption(f"Will post at **{scheduled_at_iso}** (UTC)")

            if st.button("🚀 Send to Buffer", type="primary") and selected_profile_ids:
                for idx in selected_indices:
                    ad = ads[idx]
                    variation = ad["variation"]

                    primary_val = st.session_state.get(f"primary_{idx}", variation.get("primary_text", ""))
                    headline_val = st.session_state.get(f"headline_{idx}", variation.get("headline", ""))
                    post_text = f"{primary_val}\n\n👉 {headline_val}\n\nhuntwithOdin.com"

                    img_url = st.session_state.get(f"custom_url_{idx}", "").strip()
                    if not img_url and ad["images"]:
                        radio_val = st.session_state.get(f"img_radio_{idx}")
                        img_labels = [f"Image {j+1} · {img['source']}" for j, img in enumerate(ad["images"])]
                        img_url = (
                            ad["images"][img_labels.index(radio_val)]["url"]
                            if radio_val in img_labels
                            else ad["images"][0]["url"]
                        )

                    label = f"{ad['format']} · {variation.get('angle', '')}"
                    with st.spinner(f"Sending {label}…"):
                        try:
                            post_update(
                                profile_ids=selected_profile_ids,
                                text=post_text,
                                image_url=img_url or None,
                                scheduled_at=scheduled_at_iso,
                                now=(timing == "Post immediately"),
                            )
                            st.success(f"✓ {label} sent!")
                        except Exception as e:
                            st.error(f"✗ {label} failed: {e}")
                # Invalidate cached schedule so it refreshes on next open
                st.session_state.pop("buffer_schedule", None)
