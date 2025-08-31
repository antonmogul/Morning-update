import os
from datetime import datetime
import pytz

def today_str(tz_name="America/Toronto"):
    tz = pytz.timezone(tz_name)
    return datetime.now(tz).strftime("%Y-%m-%d")

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def repo_raw_url(repo: str, branch: str, path: str) -> str:
    """
    Build a raw.githubusercontent.com URL for a committed file.
    repo: 'owner/repo'
    branch: e.g. 'main'
    path: relative path in repo (no leading slash)
    """
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
