import { Hono } from "hono";
import { cacheControl } from "../middleware/cache.js";
import type { AppEnv } from "../types.js";

export const statsRoute = new Hono<AppEnv>();

statsRoute.get("/", cacheControl(300, 900), async (c) => {
  const db = c.get("db");

  const [totalsRes, boardsRes, sourcesRes, runsRes] = await Promise.all([
    db.execute(`
      SELECT
        COUNT(*) AS active_jobs,
        COUNT(DISTINCT company_slug) AS active_companies,
        SUM(CASE WHEN remote_type = 'remote' THEN 1 ELSE 0 END) AS remote_jobs,
        SUM(CASE WHEN salary_min IS NOT NULL OR salary_max IS NOT NULL THEN 1 ELSE 0 END) AS jobs_with_salary
      FROM jobs
      WHERE is_active = 1
    `),
    db.execute(`
      SELECT
        SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active_boards,
        COUNT(*) AS total_boards
      FROM boards
    `),
    db.execute(`
      SELECT source, source_type, COUNT(*) AS count
      FROM jobs
      WHERE is_active = 1
      GROUP BY source, source_type
      ORDER BY count DESC
    `),
    db.execute(`
      SELECT id, run_type, shard, started_at, finished_at, status,
             boards_processed, jobs_upserted, jobs_expired, errors_count
      FROM ingestion_runs
      ORDER BY started_at DESC
      LIMIT 10
    `),
  ]);

  const t = totalsRes.rows[0];
  const b = boardsRes.rows[0];

  return c.json({
    data: {
      active_jobs: Number(t?.active_jobs ?? 0),
      active_companies: Number(t?.active_companies ?? 0),
      remote_jobs: Number(t?.remote_jobs ?? 0),
      jobs_with_salary: Number(t?.jobs_with_salary ?? 0),
      active_boards: Number(b?.active_boards ?? 0),
      total_boards: Number(b?.total_boards ?? 0),
      by_source: sourcesRes.rows.map((r) => ({
        source: String(r.source),
        source_type: String(r.source_type),
        count: Number(r.count),
      })),
      recent_runs: runsRes.rows.map((r) => ({
        id: Number(r.id),
        run_type: String(r.run_type),
        shard: r.shard ? String(r.shard) : null,
        started_at: String(r.started_at),
        finished_at: r.finished_at ? String(r.finished_at) : null,
        status: String(r.status),
        boards_processed: Number(r.boards_processed ?? 0),
        jobs_upserted: Number(r.jobs_upserted ?? 0),
        jobs_expired: Number(r.jobs_expired ?? 0),
        errors_count: Number(r.errors_count ?? 0),
      })),
    },
  });
});
