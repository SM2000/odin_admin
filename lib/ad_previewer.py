def render_facebook_preview(variation: dict, image_url: str | None, platform: str) -> str:
    """Return an HTML string that mimics a Facebook/Instagram ad card."""
    primary = variation.get("primary_text", "").replace("\n", "<br>")
    headline = variation.get("headline", "")
    description = variation.get("description", "")
    cta = variation.get("cta", "Learn More")

    img_html = (
        f'<img src="{image_url}" style="width:100%;max-height:340px;object-fit:cover;display:block;" />'
        if image_url
        else '<div style="width:100%;height:220px;background:#c8d6c0;display:flex;align-items:center;'
             'justify-content:center;color:#555;font-size:14px;">No image selected</div>'
    )

    is_insta = "instagram" in platform.lower()
    profile_icon = "🦌" if not is_insta else "📸"
    platform_label = "Instagram" if is_insta else "Facebook"
    brand_color = "#E1306C" if is_insta else "#1877F2"

    return f"""
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
            max-width:500px;border:1px solid #ddd;border-radius:8px;
            overflow:hidden;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.1);">
  <!-- Header -->
  <div style="display:flex;align-items:center;padding:12px 16px;gap:10px;">
    <div style="width:40px;height:40px;border-radius:50%;background:#1a3320;
                display:flex;align-items:center;justify-content:center;
                font-size:20px;">{profile_icon}</div>
    <div>
      <div style="font-weight:600;font-size:14px;">HuntWithOdin</div>
      <div style="font-size:12px;color:#65676b;">Sponsored · <span style="color:{brand_color};">{platform_label}</span></div>
    </div>
  </div>
  <!-- Body copy -->
  <div style="padding:0 16px 12px;font-size:14px;color:#1c1e21;line-height:1.5;">
    {primary}
  </div>
  <!-- Image -->
  {img_html}
  <!-- Footer / CTA -->
  <div style="display:flex;align-items:center;justify-content:space-between;
              padding:10px 16px;background:#f0f2f5;border-top:1px solid #ddd;">
    <div>
      <div style="font-size:12px;color:#65676b;text-transform:uppercase;letter-spacing:.5px;">
        huntwithOdin.com
      </div>
      <div style="font-weight:700;font-size:15px;color:#1c1e21;">{headline}</div>
      {f'<div style="font-size:13px;color:#65676b;">{description}</div>' if description else ""}
    </div>
    <button style="background:{brand_color};color:#fff;border:none;border-radius:6px;
                   padding:8px 16px;font-weight:600;font-size:14px;cursor:pointer;
                   white-space:nowrap;">
      {cta}
    </button>
  </div>
</div>
"""
