import re

CONTROL_PATTERN = re.compile(r"<\|.*?\|>")


def clean_llm_text(text: str) -> str:
    """Return LLM output with control tokens removed, preserving natural spacing."""

    if not text:
        return ""

    cleaned = CONTROL_PATTERN.sub("", text)
    cleaned = cleaned.replace("\r", "")

    filtered_lines: list[str] = []
    for raw_line in cleaned.split("\n"):
        stripped = raw_line.strip()
        if not stripped:
            filtered_lines.append("")
            continue
        if stripped.startswith("assistantcommentary to=") or stripped.startswith("commentary to="):
            continue
        filtered_lines.append(raw_line)

    result = "\n".join(filtered_lines)
    if result.startswith("assistant"):
        result = result[len("assistant") :].lstrip(": ")

    return result


__all__ = ["clean_llm_text"]
