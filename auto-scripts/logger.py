import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE_PATH = REPO_ROOT / "pipeline.log"


class CleanFormatter(logging.Formatter):
    """Clean formatter with readable timestamps and aligned log levels."""
    def format(self, record):
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        level = record.levelname.ljust(7)
        return f"[{timestamp}] [{level}] {record.getMessage()}"


def setup_logger(log_file=LOG_FILE_PATH, level=logging.INFO):
    """
    Initializes a centralized logger.
    Overwrites the log file on every run (mode='w') so each run starts clean.
    Outputs to both the log file and the console.
    """
    logger = logging.getLogger("SyllabusPipeline")
    logger.setLevel(level)

    # Clear existing handlers to prevent duplicate logs on reload
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = CleanFormatter()

    # 1. File Handler (mode='w' ensures log is overwritten from scratch)
    file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 2. Console Handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# Global logger instance
logger = setup_logger()


def log_banner(title: str):
    """Prints a prominent visual separator for pipeline phases."""
    bar = "=" * 80
    logger.info("")
    logger.info(bar)
    logger.info(f"  {title.upper()}")
    logger.info(bar)
    logger.info("")


def log_section(title: str):
    """Prints a minor section divider."""
    logger.info(f"\n--- {title} ---")


def log_info(msg: str):
    logger.info(msg)


def log_success(msg: str):
    logger.info(f"✅ [SUCCESS] {msg}")


def log_warning(msg: str):
    logger.warning(f"⚠️  [WARNING] {msg}")


def log_error(msg: str):
    logger.error(f"❌ [ERROR] {msg}")
