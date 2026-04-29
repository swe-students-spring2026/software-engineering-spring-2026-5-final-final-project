"""Compatibility shim for the `pypdf` import used by the backend.

If the real `pypdf` package is available, we use it. Otherwise we fall back to
`PyPDF2`, which exposes a compatible `PdfReader` for the code paths in this repo.
"""

try:
    from PyPDF2 import PdfReader  # type: ignore
except Exception as exc:  # pragma: no cover
    class PdfReader:  # type: ignore
        def __init__(self, *args, **kwargs):
            raise RuntimeError("PDF parsing support is unavailable") from exc
