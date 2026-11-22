"""Entry point for ``openscience-api`` (uvicorn launcher)."""


def run() -> None:
    """Run the API with uvicorn."""
    import uvicorn

    from openscience.api.config import get_settings

    settings = get_settings()
    uvicorn.run(
        "openscience.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run()
