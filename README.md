# SignalDrop

A social intelligence dashboard that identifies declining conversation trends across public Telegram channels.

Analyzes ~700K posts from 366 channels (Sep–Dec 2025) and surfaces topics whose normalized share of discussion dropped significantly from September to December.

## Architecture Overview

```
CSV → Local Python Preprocessing → SQLite In-Memory → Trend Detection → JSON Artifacts
                                                                              ↓
                                                         FastAPI Backend ← reads artifacts
                                                                              ↓
                                                         React Dashboard ← consumes API
```

The key design principle: **preprocessing is offline, the live API is fast**. The backend never touches the raw CSV — it serves precomputed JSON artifacts.

## Quick Start (Local)

### Prerequisites
- Python 3.9+
- Node.js 18+
- The Telegram CSV file (not included in repo)

### 1. Run Preprocessing

```bash
cd signaldrop-dashboard

pip install -r data_processing/requirements.txt

# Takes ~5 minutes for 700K rows
python -m data_processing.scripts.ingest_and_compute \
  --csv ~/Downloads/telegram.csv \
  --output ./artifacts \
  --top-n 30
```

Produces JSON artifacts in `./artifacts/`.

### 2. Start the Backend

```bash
cd backend
pip install -r requirements.txt

export ARTIFACTS_SOURCE=local
export ARTIFACTS_LOCAL_PATH=../artifacts

uvicorn app.main:app --reload --port 8000
```

### 3. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — Vite proxies `/api` to `localhost:8000`.

### Or just use the Makefile

```bash
make install
make preprocess CSV=~/Downloads/telegram.csv
make backend          # in one terminal
make frontend         # in another
make ai-labels        # optional
```

## Optional: AI Labeling (local-only)

If you have an Anthropic API key, you can enrich the top trends with human-readable labels, categories, and one-line explanations. The app works fully without it.

**Where the API key goes:**
- Put it in a local `.env` file at the repo root.
- `.env` is gitignored — it must **never** be committed.
- `.env.example` is safe to commit because it contains placeholders only.

Create your `.env` (one time):
```bash
cp .env.example .env
# Then edit .env and fill in ANTHROPIC_API_KEY=sk-ant-...
```

Run AI labeling:
```bash
# Option A — load .env into the shell, then run make
set -a && source .env && set +a
make ai-labels

# Option B — export the variables inline
export ANTHROPIC_API_KEY="sk-ant-..."
export ANTHROPIC_MODEL="claude-sonnet-4-6"
make ai-labels
```

**Model selection:**
- Default model: `claude-sonnet-4-6`.
- Override via `ANTHROPIC_MODEL` env var (e.g., `ANTHROPIC_MODEL=claude-haiku-4-5-20251001`).

**Output:**
- The script writes `artifacts/ai_labels.json`.
- `artifacts/` is gitignored — do **not** commit `ai_labels.json`.
- You can upload it to S3 alongside the other artifacts:
  ```
  s3://signaldrop-data-matan-2026/processed/ai_labels.json
  ```

**Behavior:**
- The backend serves `ai_labels.json` via `GET /api/ai-labels`. The frontend uses AI labels in the chart and detail panel; trends without labels fall back to the keyword.
- If `ANTHROPIC_API_KEY` is unset or empty, `make ai-labels` prints a skip message and exits cleanly.

**Important:**
- The API key is read from the **server-side environment** during preprocessing. It is **never** bundled into the frontend.
- Anthropic is called **only** during this optional preprocessing step. The live backend and frontend never call the LLM.
- Deterministic scoring remains the source of truth — AI is presentation only.

## Trend Detection Methodology

### Normalization

September has 224K posts while December has 83K. Raw counts are misleading.

We compute **monthly share** = posts mentioning topic / total posts in month. This makes months comparable regardless of volume.

### Ranking

> **Trends are ranked by normalized September-to-December decline, weighted by September topic share to avoid over-ranking tiny low-volume topics.**

```
decline_percentage = (sep_share - dec_share) / sep_share
ranking_score      = absolute_delta × decline_percentage
```

Pure `decline_percentage` alone would put every topic that went from 50 → 0 mentions ahead of every topic that went from 30K → 5K. Weighting by `absolute_delta` (which scales with September share) ensures real-volume topics rank ahead of negligible ones that vanish.

The dashboard surfaces all underlying numbers per trend: September mentions, December mentions, September share, December share, decline percentage, and ranking score.

### Filtering

- Minimum 50 September mentions
- Minimum 0.05% September share
- Minimum 30% decline
- **Home Front Command alert posts excluded** — long, comma-separated location lists from rocket-alert templates, not topical content.
- **UI boilerplate tokens removed** — words like `reading`, `mobile`, `device`, `subscribe` appear in navigation text embedded in shared posts.
- **Junk tokens removed** — long alphanumeric strings that look like URL fragments or hashes.

## AWS Deployment

| Component | Target |
|-----------|--------|
| Frontend  | AWS Amplify Hosting |
| Backend   | AWS App Runner (from `backend/Dockerfile`) |
| Data      | S3 `signaldrop-data-matan-2026` under `processed/` |

### Upload artifacts to S3

Set `ARTIFACTS_SOURCE=s3` on the backend, and upload the processed JSON to:

```
s3://signaldrop-data-matan-2026/processed/
```

Required files:
- `overview.json`
- `trends.json`
- `trend_timeseries.json`
- `channel_breakdown.json`
- `representative_posts.json`
- `methodology.json`
- `ai_labels.json` *(optional — only if you ran AI labeling)*

Helper script (uses your local AWS credentials, e.g. via `aws sso login` or `~/.aws/credentials`):

```bash
python -m data_processing.scripts.upload_to_s3 --artifacts ./artifacts
```

### App Runner environment variables (backend)

| Var | Value |
|---|---|
| `ARTIFACTS_SOURCE` | `s3` |
| `AWS_REGION` | `eu-west-2` |
| `S3_BUCKET` | `signaldrop-data-matan-2026` |
| `ARTIFACTS_PREFIX` | `processed/` |
| `CORS_ORIGINS` | `https://<your-amplify-domain>.amplifyapp.com` |

**Do not** set `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` on App Runner. Instead, attach an IAM role to the App Runner service with `s3:GetObject` on `s3://signaldrop-data-matan-2026/processed/*`. The backend uses the default boto3 credential chain, which picks up the role automatically.

### Amplify environment variables (frontend)

| Var | Value |
|---|---|
| `VITE_API_BASE_URL` | `https://<your-app-runner-url>.<region>.awsapprunner.com/api` |

Amplify reads this at build time. In local dev, leave it unset — the Vite proxy handles `/api`.

## Project Structure

```
signaldrop-dashboard/
├── backend/              # FastAPI API server
│   ├── app/
│   │   ├── main.py       # App entry point
│   │   ├── api/routes.py # REST endpoints
│   │   ├── services/     # Storage + business logic
│   │   └── config.py     # Environment config
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/             # React + TypeScript + Tailwind + Recharts
│   ├── amplify.yml
│   └── src/
│       ├── components/
│       ├── api/client.ts
│       └── types/
├── data_processing/      # Offline preprocessing pipeline
│   ├── loaders/          # BaseLoader + TelegramCsvLoader
│   ├── services/         # Cleaning, n-grams, scoring, AI labeling
│   └── scripts/          # ingest_and_compute, generate_ai_labels, upload_to_s3
├── ARCHITECTURE.md       # Scaling and design decisions
├── Makefile
├── .env.example          # Placeholders only — safe to commit
└── README.md
```

## Data Source Extensibility

The `BaseLoader` abstraction normalizes any source into:

```python
@dataclass
class NormalizedPost:
    id: str
    published_at: datetime
    content: str
    source_name: str    # e.g., channel name
    source_id: str      # e.g., channel ID
    source_type: str    # e.g., "telegram", "facebook"
```

Adding a new source (Facebook, Reddit, etc.) means writing a new loader class. The rest of the pipeline runs unchanged.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /api/overview` | Dataset summary stats |
| `GET /api/trends` | Top declining trends |
| `GET /api/trends/{topic}` | Detail: time series, channels, example posts |
| `GET /api/channels?topic=X` | Channel-level breakdown for a topic |
| `GET /api/methodology` | Scoring methodology documentation |
| `GET /api/ai-labels` | AI labels if `ai_labels.json` exists, else `{}` |

## Git Hygiene

Never commit:
- `.env` or any real secrets
- The raw CSV (`*.csv` is gitignored)
- `artifacts/` (regenerated by the pipeline)
- `node_modules/`, build outputs, `__pycache__/`
- AWS credential CSVs
- Your Anthropic API key
- `.DS_Store`, `__MACOSX/`, `.claude/`

All of the above are listed in `.gitignore`. Review `git status` carefully before your first commit.
