import os
import uuid
import requests
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from lib.claude_ad_writer import generate_ad_variations
from lib.image_fetcher import fetch_images
from lib.ad_previewer import render_facebook_preview
from lib.buffer_publisher import get_profiles, post_update, get_scheduled_posts


def _show_error(friendly: str, detail: str = "") -> None:
    """Show a user-friendly error with an optional collapsible debug block."""
    st.error(friendly)
    if detail:
        with st.expander("Debug info — paste this when reporting an issue"):
            st.code(detail, language=None)


def _friendly_claude_error(exc: Exception, context: str = "") -> tuple[str, str]:
    """Return (friendly message, raw detail) for a Claude API error."""
    raw = str(exc)
    if "529" in raw or "overloaded" in raw.lower():
        friendly = (
            "Claude's servers are temporarily busy and couldn't generate your ads. "
            "This usually clears up within a minute — please try again."
        )
    elif "401" in raw or "authentication" in raw.lower() or "api_key" in raw.lower():
        friendly = (
            "Anthropic API key problem. Check that ANTHROPIC_API_KEY is set correctly "
            "in your Render environment variables."
        )
    elif "429" in raw or "rate_limit" in raw.lower():
        friendly = "Too many requests sent to Claude at once. Wait 30 seconds and try again."
    elif "connection" in raw.lower() or "timeout" in raw.lower():
        friendly = "Couldn't reach Claude's servers — check your internet connection and try again."
    else:
        friendly = (
            f"Claude couldn't generate ads{' for ' + context if context else ''}. "
            "Try adjusting your inputs or try again in a moment."
        )
    return friendly, f"Context: {context}\n{raw}"

STATIC_UPLOADS = Path(__file__).parent / "static" / "uploads"
STATIC_UPLOADS.mkdir(parents=True, exist_ok=True)

APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8501").rstrip("/")

st.set_page_config(
    page_title="HuntWithOdin · Ad Creator",
    page_icon="🦌",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }

/* Page padding */
.main .block-container { padding-top: 1.8rem; padding-bottom: 3rem; max-width: 1280px; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #E8F5EE 0%, #EAF2F8 100%);
    border-right: 1px solid #C6E2D4;
}

/* ── Buttons ── */
.stButton > button {
    border-radius: 8px;
    font-weight: 600;
    letter-spacing: 0.3px;
    transition: all 0.18s ease;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 14px rgba(5, 150, 105, 0.25);
}
/* Primary buttons → emerald-to-blue gradient */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #059669 0%, #0284C7 100%);
    border: none;
    color: #fff;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #047857 0%, #0369A1 100%);
}
/* Secondary buttons → outlined green */
.stButton > button[kind="secondary"] {
    border: 1.5px solid #059669;
    color: #047857;
    background: transparent;
}
.stButton > button[kind="secondary"]:hover {
    background: rgba(5, 150, 105, 0.08);
}

/* ── Form card ── */
div[data-testid="stForm"] {
    background: #fff;
    border: 1px solid #C6E2D4;
    border-radius: 14px;
    padding: 1.6rem 1.8rem;
    box-shadow: 0 2px 8px rgba(5, 150, 105, 0.06);
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background: #E8F5EE;
    padding: 5px;
    border-radius: 10px;
    border: 1px solid #C6E2D4;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 7px;
    padding: 7px 16px;
    font-weight: 500;
    font-size: 0.85rem;
    color: #6B7280;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #059669 0%, #0284C7 100%) !important;
    color: #fff !important;
}

/* ── Expanders ── */
details {
    border: 1px solid #C6E2D4 !important;
    border-radius: 10px !important;
    background: #fff !important;
}
details summary { font-weight: 600; color: #047857; }

/* ── Inputs ── */
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea {
    border-radius: 8px !important;
    border-color: #C6E2D4 !important;
    background: #fff !important;
}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stTextArea"] textarea:focus {
    border-color: #059669 !important;
    box-shadow: 0 0 0 2px rgba(5, 150, 105, 0.15) !important;
}

/* ── Alerts ── */
div[data-testid="stAlert"] { border-radius: 10px; }

/* ── Dividers ── */
hr { border-color: #C6E2D4 !important; margin: 1.2rem 0 !important; }

/* ── Images ── */
img { border-radius: 10px; }

/* ── Dataframe ── */
div[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }

/* ── Progress bar ── */
div[data-testid="stProgressBar"] > div > div {
    background: linear-gradient(90deg, #059669, #0284C7) !important;
    border-radius: 99px;
}

/* ── File uploader ── */
div[data-testid="stFileUploader"] {
    border: 2px dashed #C6E2D4;
    border-radius: 10px;
    padding: 0.5rem;
    transition: border-color 0.2s;
}
div[data-testid="stFileUploader"]:hover { border-color: #059669; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("""
    <div style="padding: 1rem 0 0.5rem;">
        <div style="font-size:2rem;">🦌</div>
        <div style="font-size:1.2rem;font-weight:700;color:#047857;margin-top:4px;">HuntWithOdin</div>
        <div style="font-size:0.8rem;color:#6B7280;letter-spacing:1.5px;text-transform:uppercase;margin-top:2px;">Ad Creator</div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _save_upload(uploaded_file) -> str:
    """Save an uploaded file to static/uploads and return its public URL."""
    ext = Path(uploaded_file.name).suffix.lower() or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    (STATIC_UPLOADS / filename).write_bytes(uploaded_file.getvalue())
    return f"{APP_BASE_URL}/app/static/uploads/{filename}"


def _image_pool(ad_idx: int, fetched: list[dict]) -> list[dict]:
    """Return combined pool: fetched images + any uploads for this ad."""
    uploads = list(st.session_state.get(f"uploads_{ad_idx}", {}).values())
    return fetched + uploads


def _image_labels(images: list[dict]) -> list[str]:
    labels, counts = [], {}
    for img in images:
        src = img["source"]
        counts[src] = counts.get(src, 0) + 1
        if src in ("Pexels", "Unsplash"):
            labels.append(f"{src} · Image {counts[src]}")
        elif src == "Upload":
            labels.append(f"Uploaded · {img.get('alt', 'photo')[:22]}")
        else:
            labels.append("Custom URL")
    return labels


def _resolve_img_url(ad_idx: int, fetched: list[dict]) -> str | None:
    pool = _image_pool(ad_idx, fetched)
    custom = st.session_state.get(f"custom_url_{ad_idx}", "").strip()
    if custom:
        pool = pool + [{"url": custom, "source": "URL", "alt": "Custom URL"}]
    labels = _image_labels(pool)
    selected = st.session_state.get(f"img_select_{ad_idx}")
    if selected and selected in labels:
        return pool[labels.index(selected)]["url"]
    return pool[0]["url"] if pool else None


# ── Campaign form ─────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:1.5rem;">
    <h1 style="font-size:2rem;font-weight:700;
               background:linear-gradient(135deg,#6EE7B7 0%,#93C5FD 100%);
               -webkit-background-clip:text;-webkit-text-fill-color:transparent;
               margin-bottom:0.25rem;">
        HuntWithOdin · Ad Creator
    </h1>
    <p style="color:#9CA3AF;font-size:1rem;margin:0;">
        Select your formats and Claude will write three scroll-stopping variations for each.
    </p>
</div>
""", unsafe_allow_html=True)

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
            friendly, detail = _friendly_claude_error(e, fmt)
            _show_error(friendly, detail)
            st.stop()

        for v in variations:
            imgs = fetch_images(v.get("image_search_query", "hunting outdoor wildlife"), num_images) if num_images > 0 else []
            all_ads.append({"format": fmt, "variation": v, "images": imgs})

    progress.empty()
    st.session_state.ads = all_ads
    # Clear per-ad upload caches when new ads are generated
    for k in list(st.session_state.keys()):
        if k.startswith("uploads_") or k.startswith("custom_url_") or k.startswith("img_select_"):
            del st.session_state[k]
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
        fetched = ad["images"]

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
                # ── Upload section ────────────────────────────────────────────
                uploaded_file = st.file_uploader(
                    "Upload your own image",
                    type=["jpg", "jpeg", "png", "webp"],
                    key=f"uploader_{i}",
                )
                if uploaded_file is not None:
                    file_key = f"{uploaded_file.name}_{uploaded_file.size}"
                    cache = st.session_state.setdefault(f"uploads_{i}", {})
                    if file_key not in cache:
                        with st.spinner("Saving image…"):
                            pub_url = _save_upload(uploaded_file)
                        cache[file_key] = {
                            "url": pub_url,
                            "alt": uploaded_file.name,
                            "source": "Upload",
                        }

                # Custom URL field
                custom_url = st.text_input(
                    "Or paste a public image URL",
                    key=f"custom_url_{i}",
                    placeholder="https://…",
                )

                # ── Unified image pool ────────────────────────────────────────
                pool = _image_pool(i, fetched)
                if custom_url.strip():
                    pool = pool + [{"url": custom_url.strip(), "source": "URL", "alt": "Custom URL"}]

                selected_img_url = None
                if pool:
                    labels = _image_labels(pool)
                    chosen = st.radio(
                        "Select image",
                        labels,
                        key=f"img_select_{i}",
                    )
                    img_idx = labels.index(chosen)
                    selected_img_url = pool[img_idx]["url"]
                    st.image(selected_img_url, use_container_width=True)
                else:
                    st.caption("No images yet — upload one or add Pexels/Unsplash keys.")

                # ── Ad mockup ─────────────────────────────────────────────────
                st.divider()
                st.markdown("**Ad mockup**")
                preview_var = {
                    "primary_text": primary,
                    "headline": headline,
                    "description": description,
                    "cta": cta,
                }
                st.components.v1.html(
                    render_facebook_preview(preview_var, selected_img_url, platform),
                    height=520, scrolling=False,
                )

    # ── Publish panel ─────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Publish via Buffer")

    try:
        profiles = get_profiles()
    except Exception as e:
        st.error(f"Could not load Buffer channels: {e}")
        profiles = []

    if not profiles:
        st.warning("No Facebook or Instagram channels found in your Buffer account.")
    else:
        profile_options = {
            f"{p.get('service','').title()} · {p.get('name', p.get('id',''))}": p
            for p in profiles
        }

        # ── Existing schedule viewer ──────────────────────────────────────────
        with st.expander("📅 View existing Buffer schedule", expanded=False):
            if st.button("Refresh schedule"):
                st.session_state.pop("buffer_schedule", None)

            if "buffer_schedule" not in st.session_state:
                with st.spinner("Fetching scheduled posts…"):
                    try:
                        st.session_state.buffer_schedule = get_scheduled_posts(
                            [p["id"] for p in profile_options.values()]
                        )
                    except Exception as e:
                        st.session_state.buffer_schedule = []
                        st.error(f"Could not load schedule: {e}")

            scheduled = st.session_state.get("buffer_schedule", [])
            if not scheduled:
                st.info("No scheduled posts found in your Buffer queue.")
            else:
                import pandas as pd
                from datetime import datetime, timezone
                rows = []
                for post in scheduled:
                    channel = post.get("channel", {})
                    raw_time = post.get("dueAt", "")
                    try:
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
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

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
            selected_channels = [profile_options[k] for k in chosen_profiles]

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

            if st.button("🚀 Send to Buffer", type="primary") and selected_channels:
                for idx in selected_indices:
                    ad = ads[idx]
                    variation = ad["variation"]

                    primary_val = st.session_state.get(f"primary_{idx}", variation.get("primary_text", ""))
                    headline_val = st.session_state.get(f"headline_{idx}", variation.get("headline", ""))
                    post_text = f"{primary_val}\n\n👉 {headline_val}\n\nhuntwithOdin.com"

                    img_url = _resolve_img_url(idx, ad["images"])

                    label = f"{ad['format']} · {variation.get('angle', '')}"
                    with st.spinner(f"Sending {label}…"):
                        try:
                            post_update(
                                channels=selected_channels,
                                text=post_text,
                                image_url=img_url,
                                scheduled_at=scheduled_at_iso,
                                now=(timing == "Post immediately"),
                            )
                            st.success(f"✓ {label} sent!")
                        except Exception as e:
                            raw = str(e)
                            if "401" in raw or "403" in raw:
                                msg = "Buffer rejected the request — check your BUFFER_ACCESS_TOKEN in Render."
                            elif "channel" in raw.lower():
                                msg = "Buffer couldn't find the selected channel. Try refreshing and reselecting."
                            else:
                                msg = f"Buffer couldn't publish this ad. Try again in a moment."
                            _show_error(f"✗ {label} failed: {msg}", raw)

                st.session_state.pop("buffer_schedule", None)
