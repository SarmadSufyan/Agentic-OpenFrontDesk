"""Entrypoint for the API server: `ofd-api` (or `python -m ofd.api`)."""

from __future__ import annotations


def main() -> None:
    import uvicorn

    from ofd.core.config import settings

    uvicorn.run(
        "ofd.api.app:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=not settings.is_production,
    )


if __name__ == "__main__":
    main()
