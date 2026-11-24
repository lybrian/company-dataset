# Job Board Platform

An automated, serverless job board backend powered by **GitHub Actions**, **Turso (libSQL)**, and a **TypeScript / Hono API** ready for any frontend job board webapp.

## Architecture

- **`db/migrations/`** — Turso / SQLite schema (`boards`, `companies`, `jobs`, `ingestion_runs`, and `jobs_fts` FTS5 full-text search index with automatic triggers).
- **`pipeline/`** — Python 3.12 async (`httpx`) ingestion engine:
  - **Board Discovery** (`discover-boards.yml`, weekly): Curated public ATS registries (`LastRound`, `Kaleb`, `Moonie`, `Feashliaa`, `OpenATSFeed`, `OpenJobs`), YC directory, VC portfolio job boards (`robots.txt`-compliant), and Hacker News comments.
  - **17 ATS Platforms** (`ingest-ats.yml`, every 6h across 10 parallel shards): Greenhouse, Lever (US/EU), Ashby, SmartRecruiters, Breezy HR, Workable, Workday, BambooHR, Recruitee, Teamtailor, Personio (DE/COM), Rippling, iCIMS, Pinpoint, JOIN, **Dover**, and **Gem**.
  - **11 Direct Public Job Feeds** (`ingest-feeds.yml`, every 4h): RemoteOK, WeWorkRemotely, Arbeitnow, Remotive, Jobicy, **Himalayas**, **The Muse**, **Working Nomads**, **HN Who's Hiring**, **Landing.jobs**, and optional **USAJobs**.
- **`api/`** — TypeScript + Hono REST API (`@libsql/client`) deployable to **Cloudflare Workers**, **Vercel**, or **Node.js / Docker**.

## Quick Start

### 1. Provision Turso Database

```bash
turso db create job-board
turso db show job-board --url
turso db tokens create job-board
```

Add `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` to **GitHub Repository Settings → Secrets and variables → Actions**.

### 2. Run Locally (with local SQLite)

```bash
# Install Python pipeline
pip install -e "./pipeline[dev]"

# Initialize local SQLite DB & ingest direct feeds
job-pipeline --db-url file:local.db migrate
job-pipeline --db-url file:local.db ingest-feeds --feeds remoteok,remotive,himalayas

# Start Hono API against the same DB
cd api && npm install
TURSO_DATABASE_URL=file:../local.db npm run dev
```

### 3. API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/v1/health` | DB health check & latest completed sync timestamp |
| `GET /api/v1/health/sources` | Per-source health across all 17 ATS platforms & 11 direct feeds (add `?probe=true` for live HTTP reachability/latency checks, or `?source=<name>`) |
| `GET /api/v1/jobs` | Search (`q` via FTS5) & filter (`remote`, `employment_type`, `source`, `source_type`, `company`, `country`, `location`, `tag`, `salary_min`, `posted_since`, `sort`, `page`, `limit`) |
| `GET /api/v1/jobs/:id` | Full job detail including HTML/text description & compensation |
| `GET /api/v1/companies` | Paginated hiring companies with active job counts |
| `GET /api/v1/companies/:slug` | Company profile and active job postings |
| `GET /api/v1/filters` | Dynamic facet counts for frontend filter sidebars |
| `GET /api/v1/stats` | Board-level counts, per-source breakdown, and recent runs |
| `GET /api/v1/openapi.json` | OpenAPI 3.1 specification |

### 4. Deploy the API

- **Cloudflare Workers**: `cd api && npx wrangler secret put TURSO_DATABASE_URL && npx wrangler secret put TURSO_AUTH_TOKEN && npx wrangler deploy`
- **Docker / Fly.io / Railway**: `docker build -t job-board-api ./api && docker run -p 8787:8787 -e TURSO_DATABASE_URL=... -e TURSO_AUTH_TOKEN=... job-board-api`
