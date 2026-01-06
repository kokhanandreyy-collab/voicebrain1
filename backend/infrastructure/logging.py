import logging
import sys
import structlog
from infrastructure.config import settings

def configure_logging():
    """
    Configures structured logging for VoiceBrain.
    Uses JSON renderer for production (easier for Datadog/ELK)
    and Console renderer for development/local.
    """
    
    # Shared processors for both structlog and standard logging
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.ENVIRONMENT == "production":
        # In Prod: JSON output
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # In Dev: Nice colored console output
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard python logging to use structlog
    formatter = structlog.stdlib.ProcessorFormatter(
        # These run ONLY on `logging` calls
        foreign_pre_chain=shared_processors,
        # These run on EVERYTHING
        processors=[
             structlog.stdlib.ProcessorFormatter.remove_processors_meta,
             structlog.processors.JSONRenderer() if settings.ENVIRONMENT == "production" else structlog.dev.ConsoleRenderer(),
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    # Silence noisy libs
    logging.getLogger("uvicorn.access").handlers = [] # We might want to replace this with our own access log middleware
    logging.getLogger("uvicorn.error").handlers = []
    
    # Optional: Log that logging is set up
    log = structlog.get_logger()
    log.info("Logging configured", env=settings.ENVIRONMENT)
