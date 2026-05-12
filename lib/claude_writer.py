import json
import anthropic

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are an expert content writer for TooSteppin, a dance shoes and dancewear brand.
Write engaging, SEO-optimised blog posts that connect with dancers of all levels.
Your tone should match the brand: passionate about dance, knowledgeable, and approachable.
Always return valid JSON with the exact schema requested."""

def generate_blog_post(topic: str, keywords: list[str], tone: str, word_count: int = 800) -> dict:
    keywords_str = ", ".join(keywords) if keywords else topic
    prompt = f"""Write a blog post for the TooSteppin website about: {topic}

SEO keywords to naturally include: {keywords_str}
Tone: {tone}
Target word count: ~{word_count} words

Return ONLY valid JSON with this exact structure:
{{
  "title": "SEO-optimised blog post title",
  "meta_description": "150-160 character meta description",
  "tags": ["tag1", "tag2", "tag3"],
  "image_search_query": "concise search query to find relevant images (3-5 words)",
  "sections": [
    {{
      "type": "intro",
      "content": "Opening paragraph HTML (use <p> tags)"
    }},
    {{
      "type": "body",
      "heading": "Section heading",
      "content": "Section body HTML (use <p>, <ul>/<li>, <strong> as appropriate)"
    }},
    {{
      "type": "body",
      "heading": "Another Section heading",
      "content": "Section body HTML"
    }},
    {{
      "type": "conclusion",
      "heading": "Wrapping up / call-to-action heading",
      "content": "Closing paragraph HTML with a soft CTA linking to TooSteppin products"
    }}
  ]
}}

Write 3-5 body sections. Make the content genuinely helpful and engaging."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    # Strip markdown code fences if Claude wrapped the JSON
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())
