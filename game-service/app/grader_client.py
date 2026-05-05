"""HTTP client for grader-service.

The grader runs untrusted student code in an isolated container.
This module only knows how to call it; it does not execute code itself.
"""

from typing import Optional
import httpx

from app.config import settings


class GraderClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 15.0,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        self._base_url = (base_url or settings.grader_service_url).rstrip("/")
        self._timeout = timeout
        # transport is injectable for tests (httpx.MockTransport)
        self._transport = transport

    async def grade(
        self,
        student_code: str,
        test_code: str,
        language: str = "python",
    ) -> dict:
        async with httpx.AsyncClient(
            timeout=self._timeout,
            transport=self._transport,
        ) as client:
            response = await client.post(
                f"{self._base_url}/grade",
                json={
                    "language": language,
                    "student_code": student_code,
                    "test_code": test_code,
                },
            )
            response.raise_for_status()
            return response.json()


# module-level singleton, easy to monkeypatch in tests
grader_client = GraderClient()
