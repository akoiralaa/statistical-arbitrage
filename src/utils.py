import os
import logging
import yaml
from pathlib import Path

# Configure logging
def setup_logging(log_file="logs/trading.log", level=logging.INFO):
    """Setup logging configuration."""
    log_dir = Path(log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# Load configuration
def load_config(config_path="config.yaml"):
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config

# Create directories
def create_directories(config):
    """Create necessary directories."""
    dirs = [
        config['data']['cache_dir'],
        Path(config['logging']['file']).parent,
        'results'
    ]
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)

logger = setup_logging()