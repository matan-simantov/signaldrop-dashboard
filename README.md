# SignalDrop

SignalDrop is a social-intelligence system that analyzes public conversation datasets and detects **topic signals whose normalized share of unique deduplicated cleaned-text posts is declining over time**.

**Live demo**
- Frontend (Amplify): https://main.d1uef6okxdq4dd.amplifyapp.com
- Backend API (ECS): https://si-3819fa673ce6443abb683b4652a4105a.ecs.eu-west-2.on.aws/api

The pipeline is loader-based: any public text source (Telegram, Facebook, Reddit, etc.) can be plugged in via a `BaseLoader` that maps source-specific rows into a normalized post schema. The rest of the pipeline — text cleaning, exact-content deduplication, n-gram extraction, normalized share scoring, deterministic consolidation, display-quality filtering — runs unchanged across sources.

The currently shipped dataset is **public Telegram channels**: 693,989 observed posts, of which **593,094 are unique cleaned-text canonical posts** after exact-content deduplication; 366 channels; September–December 2025. The dashboard opens on a generic home screen with dataset cards; clicking the Telegram card opens its analysis workspace. Future loaders (Facebook, other public text sources) appear as disabled cards.

**Core principle:** all counts, shares, rankings, deduplication, and topic groupings are deterministic. AI (Anthropic) is optional and local-only — it produces human-readable labels and a short Key Findings summary from already-computed deterministic outputs. AI never calculates rankings, counts, shares, decline metrics, deduplication, or topic groups.

## Metric definition

> **Ranking score = September-to-December decline in share of unique deduplicated cleaned-text posts, weighted by September topic share.**

Two posts are considered duplicates when their cleaned content (lowercased, URL-stripped, punctuation-stripped, whitespace-collapsed) is byte-identical. For every duplicate group only the earliest-published row survives as the *canonical* post; the others are excluded from every count, share, ranking, and channel breakdown. The dataset is **observed Telegram posts** — channel attribution after dedup reflects the *first observed channel* for a cleaned-text hash, not the original source (the CSV has no forward metadata).

## Architecture Overview

```
CSV → Local Python Preprocessing → SQLite In-Memory
  → lexical topic signals → normalized trend scoring
  → deterministic post-overlap consolidation
  → deterministic display-quality flags → JSON Artifacts
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
  --top-n 30 \
  --consolidation-candidates 200
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

The initial view is a generic SignalDrop home screen with dataset cards. Click **Public Telegram Channels Dataset** to open the Telegram analysis workspace; use **← Back to datasets** in the top of the dashboard to return. Future data sources (Facebook, other public text sources) appear as disabled cards and will be enabled when their loaders ship.

### Or just use the Makefile

```bash
make install
make preprocess CSV=~/Downloads/telegram.csv
make backend          # in one terminal
make frontend         # in another
make ai-labels        # optional
make ai-insights      # optional, run after ai-labels for best wording
```

## Optional: AI Labeling and Key Findings (local-only)

If you have an Anthropic API key, you can enrich the consolidated trends with human-readable labels, categories, one-line explanations, and a short Key Findings summary. The app works fully without it.

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
make ai-insights

# Option B — export the variables inline
export ANTHROPIC_API_KEY="sk-ant-..."
export ANTHROPIC_MODEL="claude-sonnet-4-6"
make ai-labels
make ai-insights
```

**Model selection:**
- Default model: `claude-sonnet-4-6`.
- Override via `ANTHROPIC_MODEL` env var (e.g., `ANTHROPIC_MODEL=claude-haiku-4-5-20251001`).

**Output:**
- The script writes `artifacts/ai_labels.json`.
- The insights script writes `artifacts/ai_insights.json`.
- `artifacts/` is gitignored — do **not** commit `ai_labels.json` or `ai_insights.json`.
- You can upload it to S3 alongside the other artifacts:
  ```
  s3://signaldrop-data-matan-2026/processed/ai_labels.json
  s3://signaldrop-data-matan-2026/processed/ai_insights.json
  ```

**Behavior:**
- The backend serves `ai_labels.json` via `GET /api/ai-labels`. The frontend uses AI labels in the Top Trends list and detail panel; trends without labels fall back to the underlying signal.
- The backend serves `ai_insights.json` via `GET /api/ai-insights`. The frontend uses it for Key Findings when present and falls back to deterministic findings when absent.
- If `ANTHROPIC_API_KEY` is unset or empty, `make ai-labels` prints a skip message and exits cleanly.

**Important:**
- The API key is read from the **server-side environment** during preprocessing. It is **never** bundled into the frontend.
- Anthropic is called **only** during this optional preprocessing step. The live backend and frontend never call the LLM.
- Deterministic scoring and deterministic consolidation remain the source of truth. AI is presentation only: it does not calculate rankings, counts, shares, decline metrics, or topic groups.

## Trend Detection Methodology

### Deduplication (exact cleaned-content)

The CSV contains 693,989 observed rows. Many are verbatim copies of the same message forwarded across channels (e.g. identical IDF spokesperson press releases, channel ad copypasta, LLM error messages). Counting each row as independent evidence would let amplification dominate the rankings.

Before any trend calculation:

1. `clean_text(content)` = lowercased + URLs stripped + punctuation removed + whitespace collapsed.
2. SHA-1 over the cleaned text.
3. For every hash with multiple matching rows, keep one **canonical** row (earliest `published_at`, lexicographic tie-break on `id`). Other rows are flagged `is_canonical=0` and excluded from every downstream count, share, ranking, and channel breakdown.
4. Posts whose cleaned text is shorter than `MIN_CONTENT_LENGTH_FOR_DEDUP = 20` characters are **exempt** from dedup and remain distinct (typically stickers, emoji-only, 1–2 word reactions).

**Channel attribution after dedup** is the channel of the canonical row — the *first observed channel* for that cleaned-text hash. This is **not** a claim about the true original source: the CSV has no `forward_from` metadata, so we cannot identify the actual publisher. A channel that only verbatim-forwards content will not appear in any topic's channel breakdown.

For this dataset:

| Field | Value |
|---|---|
| Observed posts | 693,989 |
| Canonical posts (after dedup) | 593,094 |
| Duplicate rows collapsed | 100,895 |
| Duplicate cleaned-text hashes | 68,644 |
| of which span ≥2 channels | 63,753 |
| Short rows exempt from dedup | 25 |

### Normalization

September has 189,526 canonical posts; December has 74,242. Raw counts across months are not comparable.

**monthly_share = canonical posts mentioning topic ÷ total canonical posts in month.** Both numerator and denominator use the canonical (deduplicated) set, so the ratio is internally consistent.

### Ranking

> **Topic signals are ranked by normalized September-to-December decline in share of unique deduplicated cleaned-text posts, weighted by September topic share.**

```
decline_percentage = (sep_share - dec_share) / sep_share
ranking_score      = absolute_delta × decline_percentage
```

Pure `decline_percentage` alone would put every topic that went from 50 → 0 mentions ahead of every topic that went from 30K → 5K. Weighting by `absolute_delta` (which scales with September share) ensures real-volume topics rank ahead of negligible ones that vanish.

The dashboard surfaces all underlying numbers per trend: September mentions, December mentions, September share, December share, decline percentage, and ranking score.

### Topic Consolidation

First-pass topics are lexical n-gram signals. This is explainable, but it can produce duplicates such as `kirk`, `charlie`, and `charlie kirk`.

After raw declining signals are ranked, SignalDrop considers only a bounded candidate pool (default: top 200 raw signals) and rescans posts to build temporary post ID sets for those candidates. Candidate pairs are compared only when they are lexically plausible, such as substring relationships, reversed bigrams, same normalized words, shared compound words, or matching AI labels from a previous local run.

Signals are merged only when deterministic post-level evidence is strong:
- Jaccard overlap
- Reciprocal directional coverage
- Monthly pattern similarity
- Stronger broad-vs-narrow checks for containment pairs

One-directional containment is not enough. For example, `gaza city` may mostly appear inside `gaza`, but most `gaza` posts may not be about `gaza city`, so those remain separate unless overlap is strong and reciprocal.

For merged groups, all metrics are recomputed from the union of unique post IDs per month and channel. Counts are never summed across member signals, so posts that mention multiple member topics are not double counted.

### Display Quality

The artifacts keep all final consolidated groups, including generic lexical signals. The dashboard applies a deterministic display-quality flag to prefer topic-like groups in the main Top Trends list.

This pass can hide weak standalone terms such as `city`, `september`, `platforms`, `speech`, or partial phrase fragments like `rosh` from the main list, while keeping them in `consolidated_trends.json` for auditability.

Genericness is conservative and is not the same as being a unigram. Clear topics such as `hostages`, `qatar`, `gaza`, `hamas`, `houthi`, `trump`, and `kirk` remain displayable.

### Filtering

- Minimum 50 September mentions
- Minimum 0.05% September share
- Minimum 30% decline
- **Home Front Command alert posts excluded** — long, comma-separated location lists from rocket-alert templates, not topical content.
- **UI / social-footer boilerplate tokens removed** — `reading`, `mobile`, `device`, `subscribe`, plus platform-footer names `tiktok`, `instagram`, `facebook`, `youtube`, `twitter`, `whatsapp` (these overwhelmingly appear in "follow us on…" footer text, not as topical content).
- **Junk tokens removed** — long alphanumeric strings that look like URL fragments or hashes.

## Tradeoffs and Limitations

The metric measures **deduplicated topic signals across observed Telegram posts**, not unique original discourse. We are honest about what this dataset and pipeline can and cannot tell us.

**What we measure**
- The share of unique cleaned-text posts mentioning each topic, per month, normalized for monthly volume.
- Exact verbatim copies of a message are collapsed to one canonical post, so cross-channel forwards do not inflate a topic.
- Topic consolidation merges lexical variants (e.g. `kirk` / `charlie` / `charlie kirk`) only when post-level overlap is strong and reciprocal.

**What we deliberately do not claim**
- We do not identify the original source of a message. The CSV has no `forward_from` metadata; channel attribution after dedup reflects the *first observed channel* for a cleaned-text hash, not the actual publisher.
- We do not claim definitive public opinion, real-world discourse, or true conversation trends — only patterns in observed posts.
- We do not validate translation accuracy. Source posts are machine-translated Hebrew → English; we can only audit the consistency of the English output.

**Known limitations**
- Exact-content dedup will not collapse near-duplicates (paraphrases, partial edits, "FW:" prefixes).
- N-gram matching is lexical, not semantic — translation variance can split one real topic into multiple English signals.
- Consolidation is conservative — some near-duplicate phrasings may remain separate if reciprocal post-level overlap is not strong enough.
- Display-quality filtering hides weak standalone terms (e.g. `city`, `september`, `platforms`) from the main list but keeps them in `consolidated_trends.json` for auditability.

**Future work (not implemented for this submission)**
- Near-duplicate detection (MinHash / SimHash) to collapse paraphrased forwards.
- Hebrew-native processing on source text to avoid translation drift.
- Semantic / embedding-based topic grouping to survive lexical variance.

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
- `consolidated_trends.json`
- `trend_timeseries.json`
- `channel_breakdown.json`
- `representative_posts.json`
- `methodology.json`
- `ai_labels.json` *(optional — only if you ran AI labeling)*
- `ai_insights.json` *(optional — only if you ran AI insights)*

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
│   ├── services/         # Cleaning, n-grams, scoring, consolidation, AI presentation
│   └── scripts/          # ingest_and_compute, generate_ai_labels, generate_ai_insights, upload_to_s3
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
| `GET /api/ai-insights` | AI key findings if `ai_insights.json` exists, else `{}` |

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
