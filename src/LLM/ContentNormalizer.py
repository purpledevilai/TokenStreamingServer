def normalize_content(content) -> str:
    """Extract text from content that may be a string or a list of content blocks.

    Reasoning models (e.g. gpt-5.2-codex) and some Anthropic streaming chunks
    return content as a list of dicts with 'type' and 'text' keys rather than
    a plain string. This helper extracts and joins the text portions.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "") for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return str(content)
