import os
import sys
from loguru import logger

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def setup_loguru():
    logger.remove()

    def _not_progress(record):
        return not record["extra"].get("is_progress", False)

    logger.add(
        sys.stdout,
        level="INFO",
        filter=_not_progress,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name: <35} | {message}",
        backtrace=False,
        diagnose=False,
    )

    logger.add(
        os.path.join(PROJECT_ROOT, 'logging', 'logs.log'),
        rotation="3 MB",
        level="INFO",
        filter=_not_progress,
        compression="zip",
        retention="90 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name: <35} | {message}",
        backtrace=False,
        diagnose=False,
    )

    logger.add(
        os.path.join(PROJECT_ROOT, 'logging', 'errors.log'),
        rotation="2 MB",
        level="ERROR",
        filter=_not_progress,
        compression="zip",
        retention="6 months",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name: <35} | {message}",
        backtrace=False,
        diagnose=False,
    )

    return logger
