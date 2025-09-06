import os
import logging
from datetime import datetime
import pytz

# Set up logging
logger = logging.getLogger(__name__)

def today_str(tz_name="America/Toronto") -> str:
    """Get today's date string in specified timezone.
    
    Args:
        tz_name: Timezone name (default: America/Toronto)
        
    Returns:
        Date string in YYYY-MM-DD format
    """
    try:
        tz = pytz.timezone(tz_name)
        date_str = datetime.now(tz).strftime("%Y-%m-%d")
        logger.debug(f"Generated date string: {date_str} for timezone {tz_name}")
        return date_str
    except Exception as e:
        logger.error(f"Failed to generate date string for timezone {tz_name}: {e}")
        # Fallback to UTC
        return datetime.utcnow().strftime("%Y-%m-%d")

def ensure_dir(path: str) -> None:
    """Create directory if it doesn't exist.
    
    Args:
        path: Directory path to create
        
    Raises:
        OSError: If directory cannot be created
    """
    try:
        os.makedirs(path, exist_ok=True)
        logger.debug(f"Ensured directory exists: {path}")
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {e}")
        raise OSError(f"Cannot create directory {path}: {e}")

def repo_raw_url(repo: str, branch: str, path: str) -> str:
    """Build a raw.githubusercontent.com URL for a committed file.
    
    Args:
        repo: Repository in 'owner/repo' format
        branch: Branch name (e.g. 'main')
        path: Relative path in repo (no leading slash)
        
    Returns:
        Raw GitHub URL
        
    Raises:
        ValueError: If repo parameter is invalid
    """
    if not repo or '/' not in repo:
        logger.error(f"Invalid repo format: {repo}")
        raise ValueError(f"Repo must be in 'owner/repo' format, got: {repo}")
    
    url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
    logger.debug(f"Generated raw URL: {url}")
    return url
