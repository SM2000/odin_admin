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

Always write like a hunter talking to another hunter. No corporate speak. Be specific. Be bold."""

_MODELS = ["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"]

_TOOL = {
    "name": "output_ad_variations",
    "description": "Output the three ad copy variations as structured data.",
    "input_schema": {
        "type": "object",
        "properties": {
            "variations": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "angle":              {"type": "string"},
                        "primary_text":       {"type": "string"},
                        "headline":           {"type": "string"},
                        "description":        {"type": "string"},
                        "cta":                {"type": "string", "enum": ["Learn More", "Download", "Sign Up", "Get Started", "Try Free", "Shop Now"]},
                        "image_search_query": {"type": "string"},
                        "hook":               {"type": "string"},
                    },
                    "required": ["angle", "primary_text", "headline", "description", "cta", "image_search_query", "hook"],
                },
            }
        },
        "required": ["variations"],
    },
}


def generate_ad_variations(
    goal: str,
    audience: str,
    format: str,
    angle_notes: str,
    platform: str,
) -> list[dict]:
    char_limits = {
        "Facebook Feed":    {"primary": 125, "headline": 40, "description": 30},
        "Instagram Feed":   {"primary": 125, "headline": 40, "description": 30},
        "Facebook Story":   {"primary": 72,  "headline": 40, "description": 0},
        "Instagram Story":  {"primary": 72,  "headline": 40, "description": 0},
        "Carousel":         {"primary": 125, "headline": 40, "description": 20},
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

Each variation must use a distinctly different angle:
1. Pain point / frustration angle
2. Authority / data / expert angle
3. FOMO / season urgency angle

Call the output_ad_variations tool with all three variations."""

    client = anthropic.Anthropic(max_retries=3)
    last_error: Exception | None = None

    for model in _MODELS:
        try:
            message = client.messages.create(
                model=model,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                tools=[_TOOL],
                tool_choice={"type": "tool", "name": "output_ad_variations"},
                messages=[{"role": "user", "content": prompt}],
            )
            for block in message.content:
                if block.type == "tool_use" and block.name == "output_ad_variations":
                    return block.input.get("variations", [])
            raise RuntimeError("Model did not call the output tool.")

        except anthropic.APIStatusError as e:
            if e.status_code == 529:
                last_error = e
                continue
            raise
        except anthropic.APIConnectionError as e:
            last_error = e
            continue

    raise last_error or RuntimeError("All Claude models unavailable.")
