# Pipeline plan

## Tech stack & project layout

* **Language & Packaging:** Python 3.12 managed with `uv` (`uv init --package eu_poultry_pipeline`, code in `src/eu_poultry_pipeline/`, dependencies managed via `uv add`, executed via `uv run`)

* **HTTP & Config:** `httpx` for API requests, `python-dotenv` for environment-based configuration (`ENV=local|prod`, `DATABASE_URL`)

* **Orchestration:** Prefect 3 (`@flow` and `@task` decorators, native task retries, scheduled via `flow.serve()` or `flow.deploy()`)

* **Transformation:** Polars 2 (vectorized expressions for parsing, validation, deduplication, and time-series feature engineering)

* **Storage:** Local development on `sqlite3`; production on Supabase PostgreSQL via `psycopg` 3

* **Quality & Testing:** `ruff` for linting/formatting, `pytest` for unit testing Polars transforms and data contract rules

### Suggested repository layout

```text
eu-poultry-pipeline/
├── pyproject.toml
├── .env.example
├── src/
│   └── eu_poultry_pipeline/
│       ├── __init__.py
│       ├── config.py        # Settings via python-dotenv (local SQLite vs. Supabase Postgres)
│       ├── db.py            # Connection & upsert helpers (sqlite3 & psycopg 3)
│       ├── extract.py       # httpx client fetching DG AGRI API
│       ├── transform.py     # Polars Bronze -> Silver & Silver -> Gold logic
│       └── flows.py         # Prefect 3 @flow and @task definitions
└── tests/
    └── test_transform.py    # pytest unit tests for data contract & ML features
```

## Source

* **What:** All weekly poultry market prices across **all** EU Member States (plus `"EU"` aggregates) and all reported poultry product categories

* **Where:** European Commission (DG AGRI) Agri-food Data Portal API (`https://api.tech.ec.europa.eu/agrifood/api/poultry/prices`), no API key required

* **Format:** JSON array of objects (one JSON object per weekly price observation)

* **Terms:** Open data under European Commission reuse policy (free for commercial and non-commercial use with attribution)

## Record key

* **Granularity:** One record = one poultry product price reported for one EU Member State (or EU aggregate) in a given reporting week

* **Composite Primary Key:** `(member_state_code, product_code, begin_date)`

## Data contract (what "valid" means)

* **Required fields:** `memberStateCode`, `memberStateName`, `beginDate`, `endDate`, `weekNumber`, `productName` (and/or `productCode`), `price`, `unit`

* **Target Silver types (Polars 2 / SQL):** `String`, `String`, `Date` (`YYYY-MM-DD`), `Date` (`YYYY-MM-DD`), `Int16`, `String`, `Float64`, `String`

* **Validation rules:**

  1. `price` $> 0$ and $< 2000$ (realistic EUR/100 kg ceiling to catch unit/decimal glitches)

  2. `begin_date` $\le$ `end_date`

  3. `week_number` between $1$ and $53$

  4. `member_state_code` is non-null and $2$–$3$ uppercase characters (2-letter ISO country code or `"EU"`)

  5. `unit` is standardized (e.g., `"EUR/100kg"`)

  6. Unique on `(member_state_code, product_code, begin_date)` — enforced both in Polars (`.unique()`) and in SQLite/PostgreSQL via `PRIMARY KEY` + `ON CONFLICT DO UPDATE`

## Medallion layers

* **Bronze (`bronze_poultry_raw`):** Append-only table storing each raw `httpx` JSON response as-is (`TEXT` in SQLite, `JSONB` in Supabase PostgreSQL) alongside ingestion metadata: `batch_id`, `request_url`, `begin_date_param`, `end_date_param`, `http_status`, `record_count`, and `ingested_at_utc`

* **Silver (`silver_poultry_prices`):** Cleaned, strongly typed, deduplicated relational table. Polars parses `DD/MM/YYYY` strings to ISO dates, strips currency symbols (`€`) and whitespace from prices, enforces data contract rules (quarantining invalid rows to `silver_quarantine`), and upserts valid rows into SQLite/PostgreSQL

* **Gold (Phased ML Feature Tables):** Computed in Polars 2 from Silver, built iteratively in four phases:

  * **Phase 1 — Multi-Horizon Price Forecasting (`gold_poultry_forecast_features`):**

    * *Purpose:* Supervised time-series regression predicting next week ($t+1$) and next month ($t+4$) poultry prices per country and product.

    * *Features (grouped `.over(["member_state_code", "product_code"])`):* Lagged prices ($1, 2, 4, 52$ weeks), 4-week & 12-week rolling means and standard deviations, WoW & YoY % price changes, and cyclical week encodings $\sin\left(\frac{2\pi \cdot \text{week}}{52}\right)$, $\cos\left(\frac{2\pi \cdot \text{week}}{52}\right)$.

    * *Targets:* `target_price_1w` and `target_price_4w` (shifted backward on historical rows only, kept strictly leak-free).

  * **Phase 2 — Market Anomaly & Data Quality Detection (`gold_poultry_anomaly_features`):**

    * *Purpose:* Unsupervised outlier detection (e.g., Isolation Forest) to flag sudden market shocks (avian flu, supply disruptions) or subtle reporting glitches.

    * *Features:* Residuals from 8-week rolling medians, z-scores of weekly price jumps, peer-group divergence (country WoW change minus EU WoW change), and reporting gap flags.

  * **Phase 3 — Member State Market Clustering (`gold_member_state_profiles`):**

    * *Purpose:* Unsupervised segmentation (e.g., K-Means / Hierarchical Clustering) grouping EU countries into behavioral tiers per year and product.

    * *Features:* Annualized price volatility, seasonal amplitude (summer vs. winter spread), correlation with the `"EU"` benchmark series, and average price tier.

  * **Phase 4 — EU Benchmark Spread & Arbitrage Modeling (`gold_eu_spread_features`):**

    * *Purpose:* Cross-sectional regression predicting whether a Member State's price will converge toward or diverge from the `"EU"` average over the next 2–4 weeks.

    * *Features:* Price spread (`member_state_price - eu_avg_price`), relative price ratio (`member_state_price / eu_avg_price`), cross-sectional z-score across all EU countries in that week, and lagged spread momentum.

## Cadence & backfill strategy

* **Historical Backfill Flow:** Parameterized Prefect 3 flow (`backfill_flow(start_year=2000, end_year=2026)`) that loops year-by-year using `beginDate` and `endDate` query parameters so `httpx` payloads stay small and resumable

* **Scheduled Weekly Flow:** Source updates weekly with occasional revisions to recent weeks. Run **once a week** (e.g., Thursday morning) fetching a **rolling 4-week window** (`beginDate` = today minus $28$ days) and upserting into Silver before recomputing Gold

## What could go wrong

* **API down, rate-limited, or slow:** Prefect 3 `@task(retries=3, retry_delay_seconds=[10, 30, 90])` handles transient `httpx.TimeoutException` and $5\text{xx}$ responses automatically

* **Massive 2000–present request timeout:** Mitigated by chunking backfills by calendar year rather than pulling 26 years in one unpaged GET request

* **Schema drift or malformed price strings:** Raw payload is safely persisted in Bronze *before* Silver validation runs; unexpected fields or unparseable rows fail fast in Polars or route to `silver_quarantine` without losing raw data

* **Late-reporting EU Member States:** Handled idempotently by the 4-week rolling window + SQL `ON CONFLICT (member_state_code, product_code, begin_date) DO UPDATE`

* **Data leakage in Gold ML features:** Prevented by strictly grouping `.over(["member_state_code", "product_code"])` on chronologically sorted data and using only historical observations ($\le t$) to predict $t+h$