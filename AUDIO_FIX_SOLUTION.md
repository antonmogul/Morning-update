# Audio Playback Issue in Notion - Root Cause & Solutions

## Problem Analysis

The audio files are not playing in Notion with the error "audio format cannot be played". After investigation, the root cause is:

**GitHub raw URLs (`raw.githubusercontent.com`) don't serve audio files with proper Content-Type headers**

When Notion tries to embed audio from GitHub raw URLs:
- GitHub serves MP3 files with `Content-Type: text/plain` instead of `audio/mpeg`
- Notion's audio player requires proper MIME type headers to recognize and play audio files
- This is intentional by GitHub to discourage using raw repos for static file hosting

## Solution Options

### Option 1: Enable GitHub Pages (Recommended)
GitHub Pages serves files with correct Content-Type headers, making audio files playable in Notion.

**Implementation Steps:**

1. **Enable GitHub Pages:**
   ```bash
   # Via GitHub CLI
   gh api repos/antonmogul/Morning-update --method PATCH -f has_pages=true -f source='{"branch":"main","path":"/public"}'
   
   # Or via GitHub UI:
   # Settings → Pages → Source: Deploy from branch → Branch: main → Folder: /public
   ```

2. **Update audio URL generation in `app/utils.py`:**
   ```python
   def repo_raw_url(repo: str, branch: str, path: str) -> str:
       """Generate GitHub Pages URL instead of raw URL for audio files."""
       if not repo:
           return f"file://{path}"
       
       # Extract username and repo name
       # Format: "username/repository"
       parts = repo.split('/')
       if len(parts) == 2:
           username, repo_name = parts
           # Use GitHub Pages URL format for public directory
           # Remove 'public/' prefix from path as it's the root on Pages
           clean_path = path.replace('public/', '')
           return f"https://{username}.github.io/{repo_name}/{clean_path}"
       
       # Fallback to raw URL
       return f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
   ```

3. **Wait for GitHub Pages deployment** (usually 1-2 minutes after first enable)

### Option 2: Use Cloudinary (Free tier available)
Host audio files on Cloudinary which provides proper Content-Type headers and CDN delivery.

**Implementation:**
1. Sign up for free Cloudinary account
2. Install cloudinary SDK: `pip install cloudinary`
3. Upload audio files to Cloudinary instead of saving locally
4. Use Cloudinary URLs in Notion

### Option 3: Use AWS S3 or Google Cloud Storage
Professional solution with proper content delivery but requires cloud account setup.

### Option 4: Direct Upload to Notion (via API)
Instead of external URLs, upload audio directly to Notion.

**Limitations:**
- Notion API doesn't support direct file uploads to audio blocks
- Would need to use Notion's internal upload mechanism (not available via API)

## Quick Fix (Immediate)

While implementing the proper solution, you can:

1. **Manual workaround**: Download the MP3 files from GitHub and manually upload them to Notion
2. **Use a proxy service**: Services like `jsdelivr.net` can serve GitHub files with proper headers:
   ```python
   # In app/utils.py
   def repo_raw_url(repo: str, branch: str, path: str) -> str:
       if not repo:
           return f"file://{path}"
       # Use jsDelivr CDN for GitHub files
       return f"https://cdn.jsdelivr.net/gh/{repo}@{branch}/{path}"
   ```

## Recommended Solution: GitHub Pages

This is the best option because:
- No additional services or costs
- Integrates seamlessly with existing GitHub workflow
- Proper Content-Type headers for all file types
- CDN benefits from GitHub's infrastructure
- Audio files will be accessible at: `https://antonmogul.github.io/Morning-update/daily/YYYY-MM-DD/filename.mp3`

## Testing the Fix

After implementing:
1. Run the pipeline to generate new audio files
2. Check the Notion page to verify audio plays correctly
3. Verify URLs are using the new format in browser DevTools

## Additional Optimizations

Consider these improvements:
- **Audio compression**: Reduce file size with lower bitrate (currently 48k for OGG)
- **Format optimization**: Stick with MP3 only (best compatibility)
- **Caching**: GitHub Pages provides automatic caching headers