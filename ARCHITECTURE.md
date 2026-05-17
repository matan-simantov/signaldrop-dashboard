# Architecture & Scalability

## Current Implementation

### Design Decisions

**Offline preprocessing + precomputed artifacts**: The preprocessing pipeline runs once locally, producing small JSON files that the API serves instantly. The live backend has no database, no CSV parsing, and no heavy computation at request time.

**SQLite in-memory during preprocessing**: The assignment suggests loading data into an in-memory database. SQLite gives us SQL expressiveness for aggregation without any infrastructure dependencies. For 700K rows, it loads in ~18 seconds and fits comfortably in memory (~500MB).

**Deterministic trend detection**: N-gram frequency analysis with normalized monthly shares. No ML dependencies, no model training, fully reproducible and explainable.

**Ranking by decline weighted by significance**: `ranking_score = absolute_delta × decline_percentage`. Pure decline percentage over-ranks tiny topics that vanish; pure absolute delta over-ranks high-volume topics with minor shifts. The product balances both dimensions.

**Deterministic topic consolidation**: First-pass n-grams are treated as lexical signals, not final human topics. The pipeline then consolidates duplicate signals using post-level overlap across a bounded candidate pool. Metrics for consolidated groups are recomputed from unique post IDs, so a post that mentions multiple member signals is counted once.

**AI as presentation only**: Anthropic is optional and local-only. It can generate readable labels, explanations, and Key Findings summaries from deterministic artifacts. It never calculates rankings, counts, shares, decline metrics, or topic groups.

### Data Flow

```
Raw CSV posts
  → source loader maps rows to NormalizedPost
  → SQLite in-memory posts table
  → clean text + SHA-1 cleaned-content hash
  → mark canonical posts (exact-content dedup, earliest published_at wins)
  → all downstream steps read canonical posts only
  → tokenize + extract unigram + bigram lexical signals
  → compute normalized monthly shares (canonical numerator + denominator)
  → rank deterministic declining signals
  → consolidate duplicate signals using reciprocal post-level overlap
  → mark generic or duplicate-looking signals for display quality
  → write JSON artifacts
  → optional AI labels and AI summaries for readability
  → FastAPI serves precomputed artifacts
  → React dashboard visualizes consolidated trends
```

### Exact-Content Deduplication

The ranking metric is *share of unique deduplicated cleaned-text posts*. Cross-channel forwards and copypasta would otherwise let amplification dominate the leaderboard.

At ingest, the pipeline:
1. Computes `clean_text(content)` for every observed post.
2. SHA-1 hashes it. Posts with cleaned length below `MIN_CONTENT_LENGTH_FOR_DEDUP = 20` get a NULL hash and stay distinct (typically stickers, emoji-only, 1–2 word reactions).
3. For each hash with multiple rows, keeps the row with the earliest `published_at` (lexicographic tie-break on `id`) as the *canonical* post and flags the rest `is_canonical=0`.

All downstream stages (`compute_monthly_ngrams`, `find_representative_posts`, `build_topic_post_index`) query `WHERE is_canonical = 1`. The metric's numerator and denominator both use canonical posts, so the ratio is internally consistent.

Channel attribution after dedup reflects the **first observed channel** for a cleaned-text hash, not the original source — the CSV has no `forward_from` metadata.

### Topic Consolidation

The consolidation layer exists because lexical n-grams can split one human topic into several signals, such as `kirk`, `charlie`, and `charlie kirk`.

The implementation is intentionally conservative:
- It considers only a bounded pool of top declining raw signals, default 200.
- It builds temporary `topic -> month -> post_id set` indexes by rescanning SQLite posts.
- It compares only plausible pairs: substring relationships, reversed bigrams, same normalized words, shared compound unigrams, or same existing AI short label.
- Lexical similarity is never enough. A merge requires deterministic overlap evidence.
- New group members must validate against the group representative, avoiding chain merges where A matches B and B matches C but A does not really match C.

The merge evidence includes:
- Jaccard overlap
- Directional coverage from topic A to topic B
- Directional coverage from topic B to topic A
- Monthly pattern similarity

Broad/narrow pairs have stricter thresholds. For example, `gaza city` may mostly appear inside `gaza`, but most `gaza` posts may not be about `gaza city`. That one-directional containment is not enough; the pair must have strong reciprocal coverage and comparable post volumes.

The final `consolidated_trends.json` artifact stores only final groups and compact evidence summaries. It does not store large post ID sets.

### Display Quality Pass

The analytical artifact remains complete, but the dashboard should not over-emphasize generic fragments when clearer topic-like groups are available. A deterministic display-quality pass marks groups with:
- `display_quality_score`
- `is_displayable`
- `display_exclusion_reason`
- `quality_notes`

This pass is display-only. It does not change trend ranking, grouping, counts, shares, or stored artifacts. It conservatively hides weak standalone terms such as `city`, `september`, `platforms`, `speech`, and partial phrase fragments such as `rosh` from the main list while leaving them available through the API and artifact.

The rule intentionally avoids treating all unigrams as generic. Clear topics such as `hostages`, `qatar`, `gaza`, `hamas`, `houthi`, `trump`, and `kirk` remain displayable.

### Current Scale Profile

- **Data**: ~700K rows, 366 channels, 4 months
- **Preprocessing**: ~5 minutes on a laptop (single-threaded Python)
- **Artifact size**: ~500KB total JSON
- **API latency**: <5ms (cached JSON read)
- **Memory**: ~500MB during preprocessing, ~10MB for the running API

---

## Scaling to 10M Rows

### What Changes

| Concern | Current | At 10M |
|---------|---------|--------|
| Data storage | Local CSV | S3 partitioned by month |
| Preprocessing | Single Python process, SQLite in-memory | Batch job, DuckDB/Polars or partitioned Parquet |
| Memory | Fits in RAM | Streaming/chunked processing |
| Scheduling | Manual local run | AWS Batch or Step Functions |

### Approach

1. **Partition raw data** by month in S3 (`raw/2025-09/`, `raw/2025-10/`, etc.)
2. **Replace SQLite with DuckDB or Polars** — both handle larger-than-memory or columnar workflows better than in-memory SQLite
3. **Process in chunks**: read one month at a time, aggregate n-gram counts and candidate post sets, then merge
4. **Pre-aggregate** into Parquet intermediate files before final trend scoring and consolidation
5. **Output remains the same**: small JSON artifacts for the API, including `consolidated_trends.json`

The API and frontend stay identical — only the preprocessing step changes.

---

## Scaling to 100M Rows

### What Changes

| Concern | Current | At 100M |
|---------|---------|---------|
| Data format | CSV | Partitioned Parquet in S3 |
| Processing | Python script | AWS Glue / EMR Spark job |
| Catalog | None | AWS Glue Data Catalog |
| Querying | SQLite | Athena (ad-hoc) + precomputed aggregates |
| Scheduling | Manual | AWS Step Functions + EventBridge |
| API | Serves flat JSON | Serves materialized aggregates, optional pagination |

### Approach

1. **S3 + Parquet + Glue Data Catalog**: Raw data stored as partitioned Parquet files. Glue crawlers maintain the schema catalog.
2. **AWS Glue ETL or EMR Spark**: Distributed n-gram extraction, aggregation, and candidate post-overlap calculation. Spark handles the parallelism across partitions.
3. **Athena for ad-hoc validation** and materialized aggregate tables for repeatable outputs.
4. **Materialized artifacts**: Write final precomputed results to S3 JSON for the API.
5. **Scheduled batch jobs**: Process runs nightly or on new data arrival via S3 events → Step Functions.
6. **API unchanged**: Still serves precomputed results. No query-time computation.

### Cost Considerations

At 100M rows, the main costs are:
- Glue/EMR compute during batch processing (~minutes per run)
- S3 storage (Parquet is highly compressed)
- API remains cheap (serving static JSON from memory or S3)

---

## Supporting Multiple Data Sources

### Architecture

```
Facebook Loader ─┐
                 │
Telegram Loader ─┤──→ NormalizedPost ──→ Pipeline ──→ Artifacts
                 │
Reddit Loader ───┘
```

Each source has a dedicated loader that implements `BaseLoader.load() → Iterator[NormalizedPost]`.

### What a new loader provides:
- Field mapping (source-specific columns → normalized schema)
- Source-specific cleaning (e.g., Facebook reaction counts, Reddit markdown)
- Authentication/download logic for the source

### What stays the same:
- Text cleaning
- N-gram extraction
- Trend scoring
- Deterministic consolidation, as long as the loader supplies stable post IDs
- Artifact generation
- Backend API
- Frontend dashboard

Adding Facebook support means writing `FacebookLoader` (~50 lines) and potentially adjusting `source_type` filters in the UI.

---

## Supporting Other Infographic Types

The architecture separates:
1. **Data ingestion** (loaders)
2. **Feature extraction** (n-grams, could add sentiment, entities, etc.)
3. **Scoring** (trend detection, could add anomaly detection, correlation, etc.)
4. **Consolidation** (post-overlap grouping, could add semantic grouping later)
5. **Artifact generation** (JSON structure for the frontend)
6. **Presentation** (React components)

To add a new infographic (e.g., "emerging trends" or "sentiment shifts"):
1. Add a new scoring service alongside `trend_scoring.py`
2. Generate a new artifact (e.g., `emerging_trends.json`)
3. Add a new API endpoint
4. Add a new React component

The pipeline's modularity means new infographic types don't require rewriting existing logic.

---

## Security

- No secrets in the repository
- AWS credentials via environment variables only
- Backend reads from S3 using IAM roles (in production) or env vars (local dev)
- No user-uploaded data — the CSV is a provided dataset, not a dynamic upload
- CORS restricted to configured origins
- No database credentials (no database in production)

---

## Tradeoffs & Limitations

| Decision | Tradeoff |
|----------|----------|
| Exact-cleaned-content dedup | Collapses verbatim cross-channel forwards (100,895 rows on this dataset) and removes amplification bias; does not collapse paraphrased near-duplicates |
| First-observed channel as canonical attribution | Deterministic and explainable; not the same as the original source — the CSV has no `forward_from` metadata |
| N-grams over embeddings | Explainable and fast, but misses semantic similarity |
| Conservative post-overlap consolidation | Reduces duplicates, but intentionally leaves uncertain near-duplicates separate |
| Precomputed artifacts | Instant API responses, but requires re-running pipeline for updates |
| SQLite in-memory | Simple and fast for current scale, won't work for 10M+ rows |
| Single-process Python | No infrastructure dependencies, but limited to single-machine performance |
| No real-time streaming | Suitable for batch analysis, not live monitoring |

### Why not use embeddings/BERTopic?

For a one-day assignment with 700K posts, deterministic n-gram analysis provides:
- Immediate explainability ("this topic declined because fewer posts mention these keywords")
- No model training or GPU requirements
- Reproducible results
- Clear methodology section in the dashboard

Embeddings would add value for semantic grouping (merging "ceasefire" with "truce" with "peace talks"), but at the cost of:
- Additional dependencies (sentence-transformers, ~2GB model download)
- Processing time (~hours for 700K posts without GPU)
- Reduced explainability
- Risk to the core deliverable

The current grouping path is deliberately deterministic and explainable. A future semantic grouping layer could use embeddings or BERTopic to catch aliases like "ceasefire" and "truce", but that should be added behind the same artifact contract and validated against deterministic metrics. The LLM layer should remain presentation-only: labels and summaries from already-identified trend outputs, not ranking or grouping.
