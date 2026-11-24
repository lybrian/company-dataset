-- 0001_initial.sql
-- Turso (libSQL / SQLite) schema for the Job Board Platform.

CREATE TABLE IF NOT EXISTS _migrations (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS boards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ats TEXT NOT NULL,
    code_key TEXT NOT NULL,
    code TEXT NOT NULL,
    region TEXT,
    company_name TEXT,
    source TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active', -- active | dead | paused
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    jobs_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    last_synced_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (ats, code_key)
);

CREATE INDEX IF NOT EXISTS idx_boards_sync
    ON boards (status, last_synced_at, id);

CREATE INDEX IF NOT EXISTS idx_boards_ats
    ON boards (ats, status);

CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    website_url TEXT,
    logo_url TEXT,
    description TEXT,
    ats TEXT,
    ats_code TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_companies_name
    ON companies (name);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,             -- ats | feed
    source TEXT NOT NULL,                  -- greenhouse, lever, remoteok, himalayas, ...
    external_id TEXT NOT NULL,
    board_id INTEGER REFERENCES boards(id) ON DELETE SET NULL,
    company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
    company_name TEXT NOT NULL,
    company_slug TEXT NOT NULL,
    company_logo TEXT,
    title TEXT NOT NULL,
    description_html TEXT,
    description_text TEXT NOT NULL DEFAULT '',
    apply_url TEXT NOT NULL,
    source_url TEXT,
    location TEXT NOT NULL DEFAULT '',
    country TEXT,                          -- ISO-2 uppercase (US, GB, DE, ...) or NULL
    remote_type TEXT NOT NULL DEFAULT 'unknown', -- remote | hybrid | onsite | unknown
    employment_type TEXT NOT NULL DEFAULT 'unknown', -- full_time | part_time | contract | internship | freelance | unknown
    department TEXT,
    seniority TEXT,
    tags_json TEXT NOT NULL DEFAULT '[]',
    tags_text TEXT NOT NULL DEFAULT '',
    salary_min INTEGER,
    salary_max INTEGER,
    salary_currency TEXT,
    salary_period TEXT,                    -- year | month | hour
    content_hash TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    posted_at TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    expired_at TEXT,
    UNIQUE (source, external_id)
);

CREATE INDEX IF NOT EXISTS idx_jobs_active_posted
    ON jobs (is_active, posted_at DESC);

CREATE INDEX IF NOT EXISTS idx_jobs_active_remote
    ON jobs (is_active, remote_type, posted_at DESC);

CREATE INDEX IF NOT EXISTS idx_jobs_active_country
    ON jobs (is_active, country, posted_at DESC);

CREATE INDEX IF NOT EXISTS idx_jobs_active_source
    ON jobs (is_active, source, posted_at DESC);

CREATE INDEX IF NOT EXISTS idx_jobs_active_employment
    ON jobs (is_active, employment_type, posted_at DESC);

CREATE INDEX IF NOT EXISTS idx_jobs_company_slug
    ON jobs (company_slug, is_active, posted_at DESC);

CREATE INDEX IF NOT EXISTS idx_jobs_board_active
    ON jobs (board_id, is_active);

CREATE INDEX IF NOT EXISTS idx_jobs_salary
    ON jobs (is_active, salary_max DESC);

CREATE VIRTUAL TABLE IF NOT EXISTS jobs_fts USING fts5(
    title,
    company_name,
    location,
    department,
    tags_text,
    description_text,
    content='jobs',
    content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS jobs_ai AFTER INSERT ON jobs BEGIN
    INSERT INTO jobs_fts(rowid, title, company_name, location, department, tags_text, description_text)
    VALUES (new.rowid, new.title, new.company_name, new.location, COALESCE(new.department, ''), new.tags_text, new.description_text);
END;

CREATE TRIGGER IF NOT EXISTS jobs_ad AFTER DELETE ON jobs BEGIN
    INSERT INTO jobs_fts(jobs_fts, rowid, title, company_name, location, department, tags_text, description_text)
    VALUES ('delete', old.rowid, old.title, old.company_name, old.location, COALESCE(old.department, ''), old.tags_text, old.description_text);
END;

CREATE TRIGGER IF NOT EXISTS jobs_au AFTER UPDATE ON jobs BEGIN
    INSERT INTO jobs_fts(jobs_fts, rowid, title, company_name, location, department, tags_text, description_text)
    VALUES ('delete', old.rowid, old.title, old.company_name, old.location, COALESCE(old.department, ''), old.tags_text, old.description_text);
    INSERT INTO jobs_fts(rowid, title, company_name, location, department, tags_text, description_text)
    VALUES (new.rowid, new.title, new.company_name, new.location, COALESCE(new.department, ''), new.tags_text, new.description_text);
END;

CREATE TABLE IF NOT EXISTS ingestion_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_type TEXT NOT NULL,                -- discover | ats | feed
    shard TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL DEFAULT 'running', -- running | completed | failed
    boards_processed INTEGER NOT NULL DEFAULT 0,
    jobs_upserted INTEGER NOT NULL DEFAULT 0,
    jobs_skipped INTEGER NOT NULL DEFAULT 0,
    jobs_expired INTEGER NOT NULL DEFAULT 0,
    errors_count INTEGER NOT NULL DEFAULT 0,
    details_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_ingestion_runs_started
    ON ingestion_runs (started_at DESC);
