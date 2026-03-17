import logging


def configure_json_logging():
    # Minimal JSON-like logging to improve log parsing in centralized systems.
    # This is a lightweight fallback; a richer formatter can be swapped in later.
    try:
        logging.basicConfig(
            level=logging.INFO,
            format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
        )
    except Exception:
        pass
