def build_html(blog: dict, images: list[dict]) -> str:
    """Assemble Shopify-compatible blog post HTML from Claude output + images."""
    sections = blog.get("sections", [])
    parts: list[str] = []

    # Hero image
    if images:
        hero = images[0]
        parts.append(
            f'<img src="{hero["url"]}" alt="{_esc(hero["alt"])}" '
            f'style="width:100%;height:auto;margin-bottom:1.5rem;" />'
        )

    image_pool = images[1:]  # remaining images to sprinkle in
    image_index = 0
    body_sections_seen = 0

    for section in sections:
        stype = section.get("type")

        if stype == "intro":
            parts.append(section["content"])

        elif stype == "body":
            heading = section.get("heading", "")
            if heading:
                parts.append(f"<h2>{_esc(heading)}</h2>")
            parts.append(section["content"])
            body_sections_seen += 1
            # Insert an image after every other body section
            if body_sections_seen % 2 == 0 and image_index < len(image_pool):
                img = image_pool[image_index]
                image_index += 1
                parts.append(
                    f'<img src="{img["url"]}" alt="{_esc(img["alt"])}" '
                    f'style="width:100%;height:auto;margin:1.5rem 0;" />'
                )

        elif stype == "conclusion":
            heading = section.get("heading", "")
            if heading:
                parts.append(f"<h2>{_esc(heading)}</h2>")
            parts.append(section["content"])

    return "\n\n".join(parts)


def _esc(text: str) -> str:
    return text.replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
