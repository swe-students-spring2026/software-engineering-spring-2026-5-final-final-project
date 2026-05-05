from meme.memegen_client import (
    DEFAULT_TEMPLATE,
    MEMEGEN_API_BASE,
    build_meme_url,
    build_response,
    escape_text,
)


def test_escape_text_handles_blank_text():
    assert escape_text("   ") == "_"


def test_escape_text_encodes_memegen_special_characters():
    text = 'Hello_world? 50% off / "now"\nnew line'

    assert escape_text(text) == "Hello__world~q_50~p_off_~s_''now''~nnew_line"


def test_build_meme_url_uses_supported_template():
    url = build_meme_url("drake", "top text", "bottom text")

    assert url == f"{MEMEGEN_API_BASE}/images/drake/top_text/bottom_text.png"


def test_build_meme_url_falls_back_to_default_template():
    url = build_meme_url("unknown", "top", "bottom")

    assert url == f"{MEMEGEN_API_BASE}/images/{DEFAULT_TEMPLATE}/top/bottom.png"


def test_build_response_returns_template_text_and_url():
    response = build_response("wonka", "Question?", "Answer")

    assert response == {
        "template": "wonka",
        "top_text": "Question?",
        "bottom_text": "Answer",
        "meme_url": f"{MEMEGEN_API_BASE}/images/wonka/Question~q/Answer.png",
    }
