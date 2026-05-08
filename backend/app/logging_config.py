import logging
import logging.handlers
import sys
from pathlib import Path

from pythonjsonlogger import jsonlogger

_CATEGORIES = ["api", "auth", "movements", "admin", "errors"]
_initialized = False


def _make_handler(path: Path, level: int = logging.INFO) -> logging.Handler:
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.TimedRotatingFileHandler(
        str(path), when="midnight", backupCount=30, encoding="utf-8"
    )
    handler.setLevel(level)
    fmt = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(fmt)
    return handler


def setup_logging(log_dir: str = "/app/logs") -> None:
    global _initialized
    if _initialized:
        return
    _initialized = True

    base = Path(log_dir)
    stdout_fmt = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(stdout_fmt)
    stdout_handler.setLevel(logging.INFO)

    for name in _CATEGORIES:
        log_path = base / name / f"{name}.log"
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        logger.addHandler(_make_handler(log_path))
        logger.addHandler(stdout_handler)

    # Erros também vão para errors.log
    err_path = base / "errors" / "errors.log"
    root = logging.getLogger()
    root.setLevel(logging.WARNING)
    root.addHandler(_make_handler(err_path, level=logging.WARNING))
    root.addHandler(stdout_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
