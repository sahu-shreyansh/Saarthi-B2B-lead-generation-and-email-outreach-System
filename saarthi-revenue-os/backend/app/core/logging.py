import logging
import json
import sys

class JSONFormatter(logging.Formatter):
    """
    Structured Python JSON logging mapping dict payloads to stdout.
    Satisfies Enterprise Observability (Step 6).
    """
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "filename": record.pathname,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_record)

def configure_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    while logger.handlers:
        logger.handlers.pop()
        
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
