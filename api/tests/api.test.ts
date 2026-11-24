import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { createClient, type Client } from "@libsql/client";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { createApp } from "../src/app.js";

function splitSql(sql: string): string[] {
  const stmts: string[] = [];
  let buf: string[] = [];
  let inTrigger = false;
  for (const rawLine of sql.split(/\r?\n/)) {
    const trimmed = rawLine.trim();
    if (!trimmed || trimmed.startsWith("--")) continue;
    buf.push(rawLine);
    const upper = trimmed.toUpperCase();
    if (upper.startsWith("CREATE TRIGGER") || upper.includes(" BEGIN") || upper.endsWith("BEGIN")) {
      inTrigger = true;
    }
    if (inTrigger) {
      if (upper.endsWith("END;")) {
        stmts.push(buf.join("\n"));
        buf = [];
        inTrigger = false;
      }
    } else if (trimmed.endsWith(";")) {
      stmts.push(buf.join("\n"));
      buf = [];
    }
  }
  if (buf.length) stmts.push(buf.join("\n"));
  return stmts;
}

describe("Job Board Hono API", () => {
  let db: Client;
  let app: ReturnType<typeof createApp>;

  beforeAll(async () => {
    db = createClient({ url: ":memory:" });
    const migrationPath = resolve(__dirname, "../../db/migrations/0001_initial.sql");
    const sql = readFileSync(migrationPath, "utf-8");
    for (const stmt of splitSql(sql)) {
      await db.execute(stmt);
    }

    const now = new Date().toISOString();
    await db.execute({
      sql: `INSERT INTO boards (ats, code_key, code, company_name, source, status, jobs_count, created_at, updated_at)
            VALUES ('greenhouse', 'stripe', 'stripe', 'Stripe', 'lastround', 'active', 2, ?, ?)`,
      args: [now, now],
    });
    await db.execute({
      sql: `INSERT INTO companies (slug, name, website_url, ats, ats_code, created_at, updated_at)
            VALUES ('stripe', 'Stripe', 'https://stripe.com', 'greenhouse', 'stripe', ?, ?),
                   ('turso', 'Turso', 'https://turso.tech', NULL, NULL, ?, ?)`,
      args: [now, now, now, now],
    });
    await db.execute({
      sql: `INSERT INTO jobs (
              id, source_type, source, external_id, board_id, company_id,
              company_name, company_slug, title, description_html, description_text,
              apply_url, location, country, remote_type, employment_type,
              department, seniority, tags_json, tags_text,
              salary_min, salary_max, salary_currency, salary_period,
              content_hash, is_active, posted_at, first_seen_at, last_seen_at
            ) VALUES
            ('job-1', 'ats', 'greenhouse', 'stripe:1', 1, 1,
             'Stripe', 'stripe', 'Staff Rust Engineer', '<p>Build distributed payments in Rust</p>', 'Build distributed payments in Rust',
             'https://boards.greenhouse.io/stripe/jobs/1', 'Remote - US', 'US', 'remote', 'full_time',
             'Engineering', 'Staff', '["rust","payments"]', 'rust payments',
             210000, 260000, 'USD', 'year',
             'hash1', 1, '2026-11-20T12:00:00Z', ?, ?),
            ('job-2', 'feed', 'himalayas', 'him:2', NULL, 2,
             'Turso', 'turso', 'Senior TypeScript Developer', '<p>Edge SQLite APIs with Hono</p>', 'Edge SQLite APIs with Hono',
             'https://turso.tech/careers/2', 'Berlin, Germany', 'DE', 'hybrid', 'full_time',
             'Platform', 'Senior', '["typescript","sqlite"]', 'typescript sqlite',
             140000, 175000, 'EUR', 'year',
             'hash2', 1, '2026-11-22T12:00:00Z', ?, ?),
            ('job-expired', 'ats', 'greenhouse', 'stripe:99', 1, 1,
             'Stripe', 'stripe', 'Old Archived Role', '<p>Expired</p>', 'Expired',
             'https://boards.greenhouse.io/stripe/jobs/99', 'San Francisco, CA', 'US', 'onsite', 'full_time',
             'Engineering', 'Senior', '[]', '',
             NULL, NULL, NULL, NULL,
             'hash3', 0, '2026-01-01T00:00:00Z', ?, ?)`,
      args: [now, now, now, now, now, now],
    });
    await db.execute({
      sql: `INSERT INTO ingestion_runs (run_type, shard, started_at, finished_at, status, boards_processed, jobs_upserted)
            VALUES ('ats', '0/10', ?, ?, 'completed', 1, 2)`,
      args: [now, now],
    });

    app = createApp({ db });
  });

  afterAll(() => {
    db.close();
  });

  it("returns health metadata", async () => {
    const res = await app.request("/api/v1/health");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.status).toBe("ok");
    expect(body.active_jobs).toBe(2);
    expect(body.last_sync.run_type).toBe("ats");
  });

  it("lists active jobs with FTS5 search and filters", async () => {
    const res = await app.request("/api/v1/jobs?q=Rust&remote=remote&country=US&salary_min=200000");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.pagination.total).toBe(1);
    expect(body.data[0].id).toBe("job-1");
    expect(body.data[0].salary.max).toBe(260000);
    expect(res.headers.get("cache-control")).toContain("max-age=60");
  });

  it("sorts jobs by salary descending", async () => {
    const res = await app.request("/api/v1/jobs?sort=salary");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.map((j: { id: string }) => j.id)).toEqual(["job-1", "job-2"]);
  });

  it("rejects invalid query params with 400", async () => {
    const res = await app.request("/api/v1/jobs?remote=mars&limit=500");
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.error.code).toBe("INVALID_QUERY");
  });

  it("returns job detail and hides expired jobs", async () => {
    const ok = await app.request("/api/v1/jobs/job-2");
    expect(ok.status).toBe(200);
    const body = await ok.json();
    expect(body.data.description_html).toContain("Hono");

    const missing = await app.request("/api/v1/jobs/job-expired");
    expect(missing.status).toBe(404);
  });

  it("returns companies list and company detail", async () => {
    const listRes = await app.request("/api/v1/companies");
    expect(listRes.status).toBe(200);
    const listBody = await listRes.json();
    expect(listBody.pagination.total).toBe(2);

    const detailRes = await app.request("/api/v1/companies/stripe");
    expect(detailRes.status).toBe(200);
    const detailBody = await detailRes.json();
    expect(detailBody.data.name).toBe("Stripe");
    expect(detailBody.data.active_jobs_count).toBe(1);
    expect(detailBody.data.jobs).toHaveLength(1);
  });

  it("returns dynamic filter facets and stats", async () => {
    const filtersRes = await app.request("/api/v1/filters");
    expect(filtersRes.status).toBe(200);
    const filters = (await filtersRes.json()).data;
    expect(filters.countries.length).toBe(2);
    expect(filters.sources.length).toBe(2);

    const statsRes = await app.request("/api/v1/stats");
    expect(statsRes.status).toBe(200);
    const stats = (await statsRes.json()).data;
    expect(stats.active_jobs).toBe(2);
    expect(stats.active_companies).toBe(2);
    expect(stats.remote_jobs).toBe(1);
    expect(stats.recent_runs).toHaveLength(1);
  });

  it("serves OpenAPI 3.1 spec", async () => {
    const res = await app.request("/api/v1/openapi.json");
    expect(res.status).toBe(200);
    const spec = await res.json();
    expect(spec.openapi).toBe("3.1.0");
    expect(spec.paths["/api/v1/jobs"]).toBeDefined();
    expect(spec.paths["/api/v1/health/sources"]).toBeDefined();
  });

  it("reports per-source health across all 17 ATS and 11 feeds", async () => {
    const now = new Date().toISOString();
    await db.execute({
      sql: "UPDATE boards SET last_synced_at = ? WHERE ats = 'greenhouse'",
      args: [now],
    });
    const res = await app.request("/api/v1/health/sources");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.summary.total_sources).toBe(28);
    expect(body.probed).toBe(false);

    const gh = body.sources.find((s: { source: string }) => s.source === "greenhouse");
    expect(gh).toMatchObject({
      source: "greenhouse",
      source_type: "ats",
      status: "healthy",
      active_jobs: 1,
      active_boards: 1,
    });

    const him = body.sources.find((s: { source: string }) => s.source === "himalayas");
    expect(him).toMatchObject({
      source: "himalayas",
      source_type: "feed",
      status: "healthy",
      active_jobs: 1,
    });
  });

  it("supports ?probe=true and ?source= filtering on /api/v1/health/sources", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = (async () =>
      new Response("ok", { status: 200 })) as unknown as typeof fetch;
    try {
      const res = await app.request("/api/v1/health/sources?source=remoteok&probe=true");
      expect(res.status).toBe(200);
      const body = await res.json();
      expect(body.probed).toBe(true);
      expect(body.sources).toHaveLength(1);
      expect(body.sources[0].source).toBe("remoteok");
      expect(body.sources[0].status).toBe("healthy");
      expect(body.sources[0].live_probe.reachable).toBe(true);
      expect(body.sources[0].live_probe.http_status).toBe(200);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});
