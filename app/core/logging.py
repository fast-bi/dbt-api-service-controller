import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

class StreamToLogger(logging.Handler):
    """
    A logging handler that redirects writes to a logger instance.
    """
    def __init__(self, logger, level=logging.INFO):
        super().__init__(level)
        self.logger = logger
        self.linebuf = ''

    def emit(self, record):
        try:
            msg = self.format(record)
            self.logger.log(record.levelno, msg)
        except Exception:
            self.handleError(record)

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.level, line.rstrip())

    def flush(self):
        pass

def setup_logging(app):
    """Configure logging for the application."""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

    file_handler = RotatingFileHandler(
        log_dir / 'dbt-api-service.log',
        maxBytes=10485760,
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s'
    ))
    console_handler.setLevel(logging.INFO)

    root_logger = logging.getLogger()
    if not root_logger.handlers:
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

    # Remove handlers from app.logger and propagate to root
    app.logger.handlers = []
    app.logger.propagate = True

    app.logger.info('DBT API Service startup') 