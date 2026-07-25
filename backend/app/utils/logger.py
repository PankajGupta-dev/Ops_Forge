import logging
import sys

# Configure standard logger for OpsForge Agent 1
logger = logging.getLogger("opsforge.agent1")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [Agent 1] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def get_logger():
    return logger
