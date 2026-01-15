import logging
import sys
import structlog
from pathlib import Path

def setup_logging():
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure shared processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # 1. Console Handler - Clean, User-Friendly (INFO+)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = structlog.stdlib.ProcessorFormatter(
        # For console, we want colorful, readable output
        processor=structlog.dev.ConsoleRenderer(colors=True),
        foreign_pre_chain=processors,
    )
    console_handler.setFormatter(console_formatter)

    # 2. File Handler - Debug, Detailed (DEBUG+)
    file_handler = logging.FileHandler("logs/debug.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = structlog.stdlib.ProcessorFormatter(
        # For file, we want structured JSON or key=value for easy parsing/grepping
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=processors,
    )
    file_handler.setFormatter(file_formatter)

    # Root Logger Configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG) # capture everything at root
    root_logger.handlers = [console_handler, file_handler]

    # Structlog Configuration
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *processors,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
