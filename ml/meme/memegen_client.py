from __future__ import annotations

import re
from typing import Any

MEMEGEN_API_BASE = "https://api.memegen.link"
DEFAULT_TEMPLATE = "buzz"
SUPPORTED_TEMPLATES = ["buzz", "drake", "ds", "wonka", "fry", "doge"]


def escape_text(text: str) -> str:
    text = text.strip()
    if not text:
        return "_"

    replacements = [
        ("_", "__"),
        ("-", "--"),
        ("?", "~q"),
        ("&", "~a"),
        ("%", "~p"),
        ("#", "~h"),
        ("/", "~s"),
        ("\\", "~b"),
        ("<", "~l"),
        (">", "~g"),
        ('"', "''"),
        ("\n", "~n"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    text = re.sub(r"\s+", "_", text)
    return text or "_"


def build_meme_url(template: str, top: str, bottom: str) -> str:
    template_id = template if template in SUPPORTED_TEMPLATES else DEFAULT_TEMPLATE
    top_text = escape_text(top)
    bottom_text = escape_text(bottom)
    return f"{MEMEGEN_API_BASE}/images/{template_id}/{top_text}/{bottom_text}.png"


def build_response(template: str, top: str, bottom: str) -> dict[str, Any]:
    template_id = template if template in SUPPORTED_TEMPLATES else DEFAULT_TEMPLATE
    return {
        "template": template_id,
        "top_text": top,
        "bottom_text": bottom,
        "meme_url": build_meme_url(template_id, top, bottom),
    }
