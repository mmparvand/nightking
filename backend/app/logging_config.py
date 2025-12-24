import logging
import logging.config
import os
from typing import Any, Dict


def get_logging_config() -> Dict[str, Any]:
    log_level = os.getenv("LOG_LEVEL", "INFO")
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "level": log_level,
            }
        },
        "root": {"handlers": ["console"], "level": log_level},
    }


def configure_logging() -> None:
    logging.config.dictConfig(get_logging_config())
