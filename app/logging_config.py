"""Logging setup. A dedicated `saarthi.audit` logger carries the message trail."""
from __future__ import annotations

import logging
from logging.config import dictConfig


def configure_logging(level: str = "INFO") -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)-8s %(name)s | %(message)s"
                },
                "audit": {"format": "%(asctime)s AUDIT | %(message)s"},
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                },
                "audit": {
                    "class": "logging.StreamHandler",
                    "formatter": "audit",
                },
            },
            "loggers": {
                "saarthi": {
                    "handlers": ["console"],
                    "level": level,
                    "propagate": False,
                },
                # Separate handler so the message audit trail stays distinct.
                "saarthi.audit": {
                    "handlers": ["audit"],
                    "level": "INFO",
                    "propagate": False,
                },
            },
            "root": {"handlers": ["console"], "level": level},
        }
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"saarthi.{name}")


def get_audit_logger() -> logging.Logger:
    return logging.getLogger("saarthi.audit")
