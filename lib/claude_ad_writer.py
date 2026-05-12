import json
import anthropic

SYSTEM_PROMPT = """You are a performance marketing expert specialising in Facebook and Instagram ads
for outdoor hunting apps. You write direct-response copy that stops the scroll, speaks to hunters
authentically, and drives app downloads and subscriptions.

HuntWithOdin context:
- Smart hunt planning platform: e-scouting, tag selection, migration data, terrain analysis
- Backed by PhD wildlife biologists and data scientists
- Tagline: "The Smart Guide for Hunters" / "Draw the best tags, know the best areas"
- Pricing: Free tier, $39.95/yr (Pro), $99.95/yr (Elite)
- Key features: hotspot suggestions, scratchpad, advanced filters, saved searches
- Audience: serious hunters who want an edge — elk, deer, mule deer, pronghorn, bear, turkey

Always write like a hunter talking to another hunter. No corporate speak. Be specific. Be bold.
Return ONLY valid JSON."""


def generate_ad_variations(
    goal: str,
    audience: str,
    format: str,
    angle_notes: str,
    platform: str,
) -> list[dict]:
    char_limits = {
        "Facebook Feed": {"primary": 125, "headline": 40, "description": 30},
        "Instagram Feed": {"primary": 125, "headline": 40, "description": 30},
        "Facebook Story": {"primary": 72, "headline": 40, "description": 0},
        "Instagram Story": {"primary": 72, "headline": 40, "description": 0},
        "Carousel": {"primary": 125, "headline": 40, "description": 20},
    }
    limits = char_limits.get(format, char_limits["Facebook Feed"])

    prompt = f"""Create 3 Facebook/Instagram ad copy variations for HuntWithOdin.

Campaign goal: {goal}
Target audience: {audience}
Ad format: {format} on {platform}
Additional angle/notes: {angle_notes if angle_notes else "None"}

Character targets:
- Primary text (body): ~{limits["primary"]} chars
- Headline: ~{limits["headline"]} chars
- Description: ~{limits["description"]} chars (0 = not used for this format)

Each variation should use a distinctly different angle:
1. Pain point / frustration angle
2. Authority / data / expert angle
3. FOMO / season urgency angle

Return JSON with this exact structure:
{{
  "variations": [
    {{
      "angle": "Short angle name",
      "primary_text": "The ad body copy. Can use line breaks. Emojis OK if authentic.",
      "headline": "Short punchy headline",
      "description": "Brief description line (blank string if not used)",
      "cta": "One of: Learn More, Download, Sign Up, Get Started, Try Free, Shop Now",
      "image_search_query": "3-6 word search query for a hunting/outdoor photo that matches this ad",
      "hook": "First sentence only — the scroll-stopper"
    }}
  ]
}}"""

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw.strip())
    return data.get("variations", [])
