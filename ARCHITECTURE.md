# Architecture & Scalability

## Current Implementation

### Design Decisions

**Offline preprocessing + precomputed artifacts**: The preprocessing pipeline runs once locally, producing small JSON files that the API serves instantly. The live backend has no database, no CSV parsing, and no heavy computation at request time.

**SQLite in-memory during preprocessing**: The assignment suggests loading data into an in-memory database. SQLite gives us SQL expressiveness for aggregation without any infrastructure dependencies. For 700K rows, it loads in ~18 seconds and fits comfortably in memory (~500MB).

**Deterministic trend detection**: N-gram frequency analysis with normalized monthly shares. No ML dependencies, no model training, fully reproducible and explainable.

**Ranking by decline weighted by significance**: `ranking_score = absolute_delta × decline_percentage`. Pure decline percentage over-ranks tiny topics that vanish; pure absolute delta over-ranks high-volume topics with minor shifts. The product balances both dimensions.

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
| Preprocessing | Single Python process, SQLite in-memory | Batch job, DuckDB or partitioned Parquet |
| Memory | Fits in RAM | Streaming/chunked processing |
| Scheduling | Manual local run | AWS Batch or Step Functions |

### Approach

1. **Partition raw data** by month in S3 (`raw/2025-09/`, `raw/2025-10/`, etc.)
2. **Replace SQLite with DuckDB** — same SQL interface but handles larger-than-memory datasets via disk spilling and columnar format
3. **Process in chunks**: read one month at a time, aggregate n-gram counts per month, then merge
4. **Pre-aggregate** into Parquet intermediate files before final trend scoring
5. **Output remains the same**: small JSON artifacts for the API

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
2. **AWS Glue ETL or EMR Spark**: Distributed n-gram extraction and aggregation. Spark handles the parallelism across partitions.
3. **Materialized aggregate tables**: Write pre-aggregated results to a fast-read store (DynamoDB or S3 JSON).
4. **Scheduled batch jobs**: Process runs nightly or on new data arrival via S3 events → Step Functions.
5. **API unchanged**: Still serves precomputed results. No query-time computation.

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
4. **Artifact generation** (JSON structure for the frontend)
5. **Presentation** (React components)

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
| N-grams over embeddings | Explainable and fast, but misses semantic similarity |
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

The correct extension path: build deterministic MVP first, then optionally add an LLM labeling layer that generates human-readable descriptions for the top trends using the already-identified keywords and representative posts as context.
