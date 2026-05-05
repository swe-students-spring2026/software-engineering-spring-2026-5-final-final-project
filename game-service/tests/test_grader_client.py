import json

import httpx
import pytest

from app.grader_client import GraderClient


@pytest.mark.asyncio
async def test_grade_sends_payload_and_parses_response():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "passed": True,
                "tests_run": 9,
                "tests_passed": 9,
                "failed_test": None,
                "error_message": None,
            },
        )

    client = GraderClient(
        base_url="http://grader.test",
        transport=httpx.MockTransport(handler),
    )

    result = await client.grade(
        student_code="def leap_year(y): return True",
        test_code="import unittest\n",
    )

    assert result["passed"] is True
    assert result["tests_run"] == 9
    assert captured["url"].endswith("/grade")
    assert captured["body"]["language"] == "python"
    assert captured["body"]["student_code"].startswith("def leap_year")


@pytest.mark.asyncio
async def test_grade_strips_trailing_slash_in_base_url():
    def handler(request: httpx.Request) -> httpx.Response:
        # double slash would mean we forgot to strip
        assert "//grade" not in str(request.url).replace("http://", "")
        return httpx.Response(
            200, json={"passed": True, "tests_run": 0, "tests_passed": 0}
        )

    client = GraderClient(
        base_url="http://grader.test/",
        transport=httpx.MockTransport(handler),
    )
    await client.grade("x = 1", "import unittest")


@pytest.mark.asyncio
async def test_grade_raises_on_5xx():
    def handler(request):
        return httpx.Response(500, text="boom")

    client = GraderClient(
        base_url="http://grader.test",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await client.grade("def f(): pass", "import unittest")
