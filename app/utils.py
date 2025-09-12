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
    """Build a URL for accessing files from GitHub repository.
    
    Uses jsDelivr CDN for audio files to ensure proper Content-Type headers
    for Notion compatibility. Falls back to raw GitHub URL for other files.
    
    Args:
        repo: Repository in 'owner/repo' format
        branch: Branch name (e.g. 'main')
        path: Relative path in repo (no leading slash)
        
    Returns:
        URL for accessing the file
        
    Raises:
        ValueError: If repo parameter is invalid
    """
    if not repo or '/' not in repo:
        logger.error(f"Invalid repo format: {repo}")
        raise ValueError(f"Repo must be in 'owner/repo' format, got: {repo}")
    
    # Check if this is an audio file that needs special handling for Notion
    is_audio = path.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a'))
    
    if is_audio:
        # Use jsDelivr CDN for audio files - serves with correct Content-Type headers
        # Format: https://cdn.jsdelivr.net/gh/user/repo@branch/path
        url = f"https://cdn.jsdelivr.net/gh/{repo}@{branch}/{path}"
        logger.debug(f"Generated jsDelivr CDN URL for audio: {url}")
    else:
        # Use standard raw GitHub URL for non-audio files
        url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
        logger.debug(f"Generated raw GitHub URL: {url}")
    
    return url
