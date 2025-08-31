# Definition of Done (DoD)

## A. Repo & Code
- Repo contains the folders/files exactly as specified earlier (`.github/workflows/daily-brief.yml`, `app/*.py`, `requirements.txt`, optional `README.md`, and this `RUNBOOK.md`).
- `requirements.txt` installs cleanly on a fresh machine (`pip install -r requirements.txt`).
- `daily-brief.yml` installs ffmpeg in CI and runs `python -m app.main` without module errors.

## B. Notion Setup
- A Notion integration (internal) exists, with secret token copied.
- Your Daily Notes database is created and shared with the integration.
- You captured the Database ID (32-char ID) correctly.
- The Title property name in that DB is known (default `Name`) or set via `NOTION_DAILY_TITLE_PROP`.

## C. Secrets / Config
- GitHub Actions secrets are set:
  - `OPENAI_API_KEY`
  - `NOTION_TOKEN`
  - `NOTION_DAILY_DB_ID`
  - (optional) `NOTION_DAILY_TITLE_PROP` (defaults to `Name`)
  - (optional) `NEWS_IMPORTANCE_THRESHOLD` (e.g., `70`)
- Timezone configured via workflow env (`TZ=America/Toronto`).
- Branch has push permission for the Actions bot (`contents: write`).

## D. First Manual Test (Local or Actions)
- You ran once manually (local or via “Run workflow”) without errors.
- The run created a new folder: `public/daily/YYYY-MM-DD/`.
- Inside that folder, there’s: `roundup.ogg` and one `.ogg` per section (e.g., `guardian.ogg`, `bbc.ogg`, etc.).
- The workflow’s “Commit audio + log updates” step pushed those files to the repo.

## E. Notion Output
- A new page exists in your Daily Notes DB titled `YYYY-MM-DD`.
- The page includes:
  - A Roundup section (could say “No items met the threshold” if nothing scored high enough).
  - One section per feed group with bullet summaries.
  - An Audio block for Roundup.
  - An Audio block for each section.
  - Clicking the audio blocks plays audio (the `raw.githubusercontent.com` links resolve).

## F. Notification
- A Notion comment appears on the page (“✅ Daily news brief is ready…”).
- You receive a push notification in Notion (optional; depends on your Notion settings).

## G. Roundup Logic
- Lowering `NEWS_IMPORTANCE_THRESHOLD` yields more items in Roundup; raising it yields fewer/none.
- Articles are clearly within the last 24h (or your configured window).

## H. Reliability & Hygiene
- The job runs on the correct schedule (07:30 Montreal; cron set for DST and non-DST).
- Subsequent runs append a new page each day and commit a new day folder.
- Repo size remains manageable (consider a cleanup job after 30 days—optional).
- Secrets are stored only in GitHub → Actions → Secrets (not in repo).

---

# Runbook

Purpose: How to configure, run, verify, and maintain the Daily Audio Brief pipeline.
Audience: You (Anton) and any developer/operator (Codex).

## 1) What this does
- Pulls multiple RSS feeds (Guardian, BBC, Montreal Gazette, AI).
- Scores each story for importance; creates a Roundup of only high-importance items.
- Summarizes each section into short bullets.
- Generates separate audio files per section plus a Roundup audio.
- Creates/updates a Notion Daily Note (`YYYY-MM-DD`) with text + audio blocks.
- Leaves a Notion comment to notify you.

Runs automatically weekdays 07:30 America/Toronto via GitHub Actions.
You can also run manually from the Actions tab.

## 2) One-time Setup
### A) Notion
1. Create a Notion Integration (internal) → copy the secret token.
2. Create a Notion database for Daily Notes (a table). The Title property should be the first column (default name `Name`).
3. Share that database with your integration:
   - Open the DB → Share (top-right) → invite your integration.
4. Copy the database ID:
   - Open the database in a browser. The long URL contains the database ID (32 characters) right after `/` and before `?` or the next `/`.

### B) GitHub Repo Secrets
In **Repo → Settings → Secrets and variables → Actions → New repository secret**, add:

| Secret name | Example/Notes |
|-------------|---------------|
| `OPENAI_API_KEY` | `sk-…` |
| `NOTION_TOKEN` | `secret_…` (Notion integration token) |
| `NOTION_DAILY_DB_ID` | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `NOTION_DAILY_TITLE_PROP` | (optional; default `Name`) |
| `NEWS_IMPORTANCE_THRESHOLD` | (optional; default `70`) |

No secrets should be committed to the repo.

## 3) How to Run
### A) Manual local test (optional)
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Temporary env vars for local test; do NOT commit
export OPENAI_API_KEY=sk-...
export NOTION_TOKEN=secret_...
export NOTION_DAILY_DB_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export NOTION_DAILY_TITLE_PROP=Name
export NEWS_IMPORTANCE_THRESHOLD=70
export TZ=America/Toronto
export GITHUB_REPO="your-username/your-repo"
export GITHUB_REF_NAME="main"

python -m app.main
```
Verify locally:
- A new folder `public/daily/YYYY-MM-DD/` is created with `.ogg/.mp3` files.
- If you commit and push that folder, Notion audio blocks will render once the Action updates the page with raw URLs.

### B) Manual run in GitHub Actions
- Go to **Actions → Daily Brief → Run workflow** (select branch; run).
- Open the latest run → confirm green checks.
- The step “Commit audio + log updates” should push audio files back to the repo.

### C) Automatic schedule
- The workflow is set to run weekdays 07:30 Montreal (handles DST/EST via two crons).
- You can change schedule in `.github/workflows/daily-brief.yml`.

## 4) Daily Human Checklist
- Open Notion → Daily Notes DB → open today’s page:
  - Skim Roundup first (high-importance only).
  - Play a specific section’s audio for detail.
- Adjust `NEWS_IMPORTANCE_THRESHOLD` in GitHub secrets if Roundup is too busy/sparse.
- Update feeds in `app/news.py` if a source is noisy or missing.

## 5) Troubleshooting
**Problem: No Notion page created**
- Check the Actions logs for errors in `Run brief`.
- Confirm `NOTION_TOKEN`, `NOTION_DAILY_DB_ID`, and sharing permissions.

**Problem: Audio blocks show broken links / don’t play**
- Ensure the commit step ran and pushed files.
- Confirm `GITHUB_REPO` and `GITHUB_REF_NAME` are set in the job env.
- Try opening the raw audio URL directly.

**Problem: Roundup says “No items met the threshold”**
- Lower `NEWS_IMPORTANCE_THRESHOLD` in secrets.
- Ensure there were fresh stories (pipeline filters to last 24h).

**Problem: Rate limits or cost concerns**
- Reduce number of items summarized (`max_items` in `summarize_items`).
- Limit feeds, or run fewer days (adjust cron).

**Problem: Notion comment didn’t ping me**
- Check your Notion notification settings.
- You can @mention yourself programmatically later using Notion mentions.

## 6) Customization
- Feeds: edit `app/news.py` → `DEFAULT_FEEDS`.
- Freshness window: change `since_hours` in `fetch_feeds` call (currently `24`).
- Summary length: adjust summarizer prompt or `max_items`.
- Audio format: we generate `.mp3` and publish `.ogg`; swap if you prefer `.mp3` embeds.
- Schedule: edit cron lines in the workflow.

## 7) Maintenance
- Consider adding a second workflow to delete folders older than 30 days.
- Rotate API keys if compromised.
- Keep `requirements.txt` up to date; pin versions for reproducibility.

## 8) Acceptance Criteria (Quick Test Plan)
1. Run (manual or scheduled) completes with ✅ in Actions.
2. Repo has `public/daily/YYYY-MM-DD/roundup.ogg` and one `.ogg` per section.
3. Notion has a new page `YYYY-MM-DD` with:
   - Roundup text
   - Section summaries
   - Audio blocks (Roundup + each section)
4. Clicking audio in Notion plays from GitHub Raw.
5. A Notion comment is posted to that page (“✅ Daily news brief is ready…”).
6. Adjusting `NEWS_IMPORTANCE_THRESHOLD` changes the number of Roundup items on next run.

## 9) Keys & Where They Live
All in **GitHub → Actions → Secrets**:
- `OPENAI_API_KEY`
- `NOTION_TOKEN`
- `NOTION_DAILY_DB_ID`
- `NOTION_DAILY_TITLE_PROP` (optional)
- `NEWS_IMPORTANCE_THRESHOLD` (optional)

Never commit keys to the repo. For local tests, export env vars only in your shell session.

