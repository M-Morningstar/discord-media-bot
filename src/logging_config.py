from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime


class _JsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON line.

    Suitable for structured-log pipelines (Datadog, ELK, Loki).
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            payload["exception"] = str(record.exc_info[1])
        return json.dumps(payload)


def setup_logging(level: str) -> None:
    """Configure root logger.

    When stdout is a TTY (terminal dev mode): human-readable colored format.
    When stdout is not a TTY (Docker/pipe): structured JSON lines.
    """
    log_level = getattr(logging, level.upper())

    if sys.stdout.isatty():
        handler: logging.Handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
    else:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_JsonFormatter())

    logging.basicConfig(level=log_level, handlers=[handler], force=True)

    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
