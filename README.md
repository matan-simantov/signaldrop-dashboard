# SignalDrop

SignalDrop is a social-intelligence system that analyzes public text datasets and detects **topic signals whose normalized share of unique deduplicated cleaned-text posts is declining over time**.

The currently shipped dataset is **public Telegram channels**: 693,989 observed posts, of which **593,094 are unique cleaned-text canonical posts** after exact-content deduplication; 366 channels; September–December 2025. The dashboard opens on a generic home screen with dataset cards; clicking the Telegram card opens its analysis workspace.

**Core principle:** all counts, shares, rankings, deduplication, and topic groupings are deterministic. AI (Anthropic) is optional and local-only — it produces human-readable labels and a short Key Findings summary from already-computed deterministic outputs. AI never calculates rankings, counts, shares, decline metrics, deduplication, or topic groups.

## Live demo

- **Dashboard**: https://main.d1uef6okxdq4dd.amplifyapp.com

Sample backend endpoints (FastAPI on AWS ECS):

- Health check: https://si-3819fa673ce6443abb683b4652a4105a.ecs.eu-west-2.on.aws/health
- Sample API: https://si-3819fa673ce6443abb683b4652a4105a.ecs.eu-west-2.on.aws/api/overview

## Metric definition

> **Ranking score = September-to-December decline in share of unique deduplicated cleaned-text posts, weighted by September topic share.**

Two posts are considered duplicates when their cleaned content (lowercased, URL-stripped, punctuation-stripped, whitespace-collapsed) is byte-identical. For every duplicate group only the earliest-published row survives as the *canonical* post; the others are excluded from every count, share, ranking, and channel breakdown. The dataset is **observed Telegram posts** — channel attribution after dedup reflects the *first observed channel* for a cleaned-text hash, not the original source (the CSV has no forward metadata).

## Findings

All numbers below are post-deduplication, computed deterministically by the pipeline. They are also visible in the dashboard's overview cards and per-trend detail panels.

- **Conflict topics dominated September but cooled sharply.** Gaza was the largest topic in September (14.1% of canonical posts) and declined to 8.3% by December — a 41% normalized decline. Hamas followed the same pattern (10.4% → 5.7%, 45% decline).
- **Hostage discourse declined more steeply than the broader conflict.** Hostages dropped 74% (9,320 → 934 canonical posts), and the narrower "release hostages" signal dropped 94% (2,274 → 57). The operational-status thread faded faster than the war framing.
- **Diplomacy nodes (Qatar, Doha) faded with hostage talks.** Qatar declined 77% (7,054 → 639) and Doha declined 84% (2,756 → 168), tracking the hostage-negotiation news cycle.
- **One-off news events vanished as expected.** Charlie Kirk — consolidated from three lexical variants (`kirk`, `charlie`, `charlie kirk`) by reciprocal post-overlap evidence — declined 96% (2,719 → 43). Yemen / Houthi discourse declined 80% and 93% respectively.
- **Cross-channel amplification was non-trivial.** 100,895 rows (14.5% of the dataset) were collapsed by exact cleaned-text dedup; 92% of duplicate groups spanned two or more channels. Without dedup, identical IDF press releases forwarded to 30+ channels would inflate those topics.
- **Footer artifacts were genuine noise.** `tiktok`, `instagram`, `whatsapp` n-grams ranked high under naive token counting because of "follow us on…" footer text. They are filtered before scoring; real declining signals replaced them.

## Architecture Overview

```
CSV → Local Python Preprocessing → SQLite In-Memory
  → exact-content deduplication (canonical post selection)
  → lexical topic signals → normalized trend scoring
  → deterministic post-overlap consolidation
  → deterministic display-quality flags → JSON Artifacts
                                                        ↓
                                   FastAPI Backend ← reads artifacts
                                                        ↓
                                   React Dashboard ← consumes API
```

The pipeline is loader-based: any public text source (Telegram, Facebook, Reddit, etc.) can be plugged in via a `BaseLoader` that maps source-specific rows into a normalized post schema. The rest of the pipeline — text cleaning, exact-content deduplication, n-gram extraction, normalized share scoring, deterministic consolidation, display-quality filtering — runs unchanged across sources.

The key design principle: **preprocessing is offline, the live API is fast**. The backend never touches the raw CSV — it serves precomputed JSON artifacts.

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

### Topic Consolidation

First-pass topics are lexical n-gram signals. This is explainable, but it can produce duplicates such as `kirk`, `charlie`, and `charlie kirk`.

After raw declining signals are ranked, SignalDrop considers only a bounded candidate pool (default: top 200 raw signals) and rescans posts to build temporary post ID sets for those candidates. Candidate pairs are compared only when they are lexically plausible (substring relationships, reversed bigrams, same normalized words, shared compound words, or matching AI labels from a previous local run).

Signals are merged only when deterministic post-level evidence is strong: Jaccard overlap, reciprocal directional coverage, monthly pattern similarity, and stronger broad-vs-narrow checks for containment pairs. One-directional containment is not enough — for example, `gaza city` may mostly appear inside `gaza`, but most `gaza` posts may not be about `gaza city`, so those remain separate unless overlap is strong and reciprocal.

For merged groups, all metrics are recomputed from the union of unique post IDs. Counts are never summed across member signals, so posts that mention multiple member topics are not double counted.

### Display Quality

The artifacts keep all final consolidated groups, including generic lexical signals. The dashboard applies a deterministic display-quality flag to prefer topic-like groups in the main Top Trends list. Weak standalone terms (`city`, `september`, `platforms`, `speech`) and partial phrase fragments (`rosh`) are hidden from the main list while remaining in `consolidated_trends.json` for auditability. Clear topics such as `hostages`, `qatar`, `gaza`, `hamas`, `houthi`, `trump`, and `kirk` remain displayable.

### Filtering

- Minimum 50 September mentions
- Minimum 0.05% September share
- Minimum 30% decline
- **Home Front Command alert posts excluded** — long comma-separated location lists from rocket-alert templates, not topical content.
- **UI / social-footer boilerplate tokens removed** — `reading`, `mobile`, `device`, `subscribe`, plus platform-footer names `tiktok`, `instagram`, `facebook`, `youtube`, `twitter`, `whatsapp` (these overwhelmingly appear in "follow us on…" footer text).
- **Junk tokens removed** — long alphanumeric strings that look like URL fragments or hashes.

## Metrics & Dimensions

| Metric | Definition |
|---|---|
| **Observed posts** | Raw CSV rows after schema parsing (693,989). |
| **Canonical posts** (unique deduplicated cleaned-text) | Rows that survive exact-cleaned-content dedup (593,094). The metric's denominator. |
| **Monthly share** | Canonical mentions of a topic ÷ total canonical posts in that month. |
| **September → December decline** | Absolute: `sep_share − dec_share`. Percentage: `(sep_share − dec_share) ÷ sep_share`. |
| **Ranking score** | `absolute_delta × decline_percentage`. Weights decline by September topic share so tiny vanishing topics don't outrank real shifts. |
| **Mentions** | Number of canonical posts containing the topic n-gram in a month. |

| Dimension | Values |
|---|---|
| **Month** | 2025-09, 2025-10, 2025-11, 2025-12 |
| **Topic / consolidated topic group** | Lexical n-gram or post-overlap-merged group (e.g. `kirk` + `charlie` + `charlie kirk`). |
| **First observed channel** | Channel of the canonical (earliest-observed) row for a given cleaned-text hash. *Not* the original source — the CSV has no forward metadata. |

## Tradeoffs and Limitations

The metric measures **deduplicated topic signals across observed Telegram posts**, not unique original discourse.

**What we measure**
- The share of unique cleaned-text posts mentioning each topic, per month, normalized for monthly volume.
- Exact verbatim copies of a message are collapsed to one canonical post, so cross-channel forwards do not inflate a topic.
- Topic consolidation merges lexical variants (e.g. `kirk` / `charlie` / `charlie kirk`) only when post-level overlap is strong and reciprocal.

**What we deliberately do not claim**
- We do not identify the original source of a message. The CSV has no `forward_from` metadata; channel attribution after dedup reflects the *first observed channel*, not the actual publisher.
- We do not claim definitive public opinion or real-world discourse — only patterns in observed posts.
- We do not validate translation accuracy. Source posts are machine-translated Hebrew → English; we can audit consistency of the English output but cannot verify against the Hebrew source.

**Known limitations**
- Exact-content dedup will not collapse near-duplicates (paraphrases, partial edits, "FW:" prefixes).
- N-gram matching is lexical, not semantic — translation variance can split one real topic into multiple English signals.
- Consolidation is conservative — some near-duplicates may remain separate if reciprocal post-level overlap is not strong enough.

**Future work**
- Near-duplicate detection (MinHash / SimHash) to collapse paraphrased forwards.
- Hebrew-native processing on source text to avoid translation drift.
- Semantic / embedding-based topic grouping to survive lexical variance.

## Quick Start (Local)

Requires Python 3.9+ and Node.js 18+. The raw Telegram CSV is not in the repo — point `--csv` at your local copy.

```bash
make install                                   # installs both backend and frontend deps
make preprocess CSV=~/Downloads/telegram.csv   # ~5 min for 700K rows; writes ./artifacts/
make backend                                   # FastAPI on :8000  (terminal 1)
make frontend                                  # Vite on :5173     (terminal 2)
```

Open http://localhost:5173. Vite proxies `/api` to `localhost:8000`. Click the **Public Telegram Channels Dataset** card to open the analysis workspace.

## Optional: AI Labeling and Key Findings

The dashboard works fully without AI. With an Anthropic API key you can enrich the trends with short labels and a Key Findings summary.

- AI is **optional, local-only, and presentation-only.** Called only during offline preprocessing. The live backend and frontend never call the LLM and the API key is never bundled into the frontend.
- AI is **never** used to compute counts, shares, rankings, decline metrics, deduplication, or topic groups.

```bash
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY=sk-ant-...   (.env is gitignored)

set -a && source .env && set +a
make ai-labels
make ai-insights
```

Outputs `artifacts/ai_labels.json` and `artifacts/ai_insights.json`. Upload to S3 alongside the other artifacts with `python -m data_processing.scripts.upload_to_s3 --artifacts ./artifacts` if you want them served by the live backend.

## AWS Deployment

| Component | Target |
|---|---|
| Frontend | AWS Amplify Hosting (monorepo, `appRoot=frontend`) |
| Backend  | AWS ECS (Express Mode), Docker image built for `linux/amd64` and pushed to ECR |
| Data     | S3 `signaldrop-data-matan-2026` under `processed/` |

### Upload artifacts to S3

```bash
python -m data_processing.scripts.upload_to_s3 --artifacts ./artifacts
```

Uploads to `s3://signaldrop-data-matan-2026/processed/`. Required files: `overview.json`, `trends.json`, `consolidated_trends.json`, `trend_timeseries.json`, `channel_breakdown.json`, `representative_posts.json`, `methodology.json`. Optional: `ai_labels.json`, `ai_insights.json`.

### Backend (ECS) environment variables

| Var | Value |
|---|---|
| `ARTIFACTS_SOURCE` | `s3` |
| `AWS_REGION` | `eu-west-2` |
| `S3_BUCKET` | `signaldrop-data-matan-2026` |
| `ARTIFACTS_PREFIX` | `processed/` |
| `CORS_ORIGINS` | `https://<amplify-domain>.amplifyapp.com` (or `*` for development) |

**Do not** set `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` on the ECS task. The task definition's **task role** (separate from the execution role) must include `s3:GetObject` on `s3://signaldrop-data-matan-2026/processed/*`. The backend uses the default boto3 credential chain and picks up the role automatically.

The backend caches artifacts in memory at startup. After re-uploading to S3, force a new deployment so the new task fetches the updated artifacts:

```bash
aws ecs update-service --cluster default --service signaldrop-backend \
  --force-new-deployment --region eu-west-2
```

### Frontend (Amplify) environment variables

| Var | Value |
|---|---|
| `VITE_API_BASE_URL` | `https://<ecs-public-url>.eu-west-2.on.aws/api` |

Amplify reads this at build time. In local dev, leave it unset — the Vite proxy handles `/api`.

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

Adding a new source means writing a new loader class. The rest of the pipeline — dedup, cleaning, n-grams, scoring, consolidation, display-quality, AI presentation — runs unchanged.

## Project Layout

- `backend/` — FastAPI API server (`app/`, `Dockerfile`, `requirements.txt`)
- `frontend/` — React + TypeScript + Tailwind + Recharts (`src/`, `amplify.yml`)
- `data_processing/` — offline preprocessing pipeline (`loaders/`, `services/`, `scripts/`)
- `Makefile` — install / preprocess / backend / frontend / ai-labels / ai-insights
- `ARCHITECTURE.md` — design decisions, scaling discussion, security
- `.env.example` — placeholders only; safe to commit

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /health` | Health check |
| `GET /api/overview` | Dataset summary stats (canonical and observed counts, dedup block) |
| `GET /api/trends` | Top declining trends |
| `GET /api/trends/{topic}` | Detail: time series, channels, example posts |
| `GET /api/channels?topic=X` | Channel-level breakdown for a topic |
| `GET /api/methodology` | Scoring methodology documentation |
| `GET /api/ai-labels` | AI labels if `ai_labels.json` exists, else `{}` |
| `GET /api/ai-insights` | AI key findings if `ai_insights.json` exists, else `{}` |
