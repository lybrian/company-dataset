import { Hono } from "hono";
import { cacheControl } from "../middleware/cache.js";
import type { AppEnv } from "../types.js";

export const healthRoute = new Hono<AppEnv>();

export const ALL_ATS_SOURCES = [
  "ashby",
  "bamboohr",
  "breezy",
  "dover",
  "gem",
  "greenhouse",
  "icims",
  "join",
  "lever",
  "personio",
  "pinpoint",
  "recruitee",
  "rippling",
  "smartrecruiters",
  "teamtailor",
  "workable",
  "workday",
] as const;

export const FEED_PROBE_URLS: Record<string, string> = {
  remoteok: "https://remoteok.com/api",
  weworkremotely: "https://weworkremotely.com/remote-jobs.rss",
  arbeitnow: "https://www.arbeitnow.com/api/job-board-api?page=1",
  remotive: "https://remotive.com/api/remote-jobs?limit=1",
  jobicy: "https://jobicy.com/api/v2/remote-jobs?count=1",
  himalayas: "https://himalayas.app/jobs/api?limit=1",
  themuse: "https://www.themuse.com/api/public/jobs?page=1",
  workingnomads: "https://www.workingnomads.com/api/exposed_jobs/",
  hn_hiring: "https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring&hitsPerPage=1",
  landingjobs: "https://landing.jobs/api/v1/jobs?limit=1",
  usajobs: "https://data.usajobs.gov/api/search",
};

export const ALL_FEED_SOURCES = Object.keys(FEED_PROBE_URLS);

const STALE_THRESHOLD_MS = 48 * 3600 * 1000; // 48 hours

interface LiveProbeResult {
  reachable: boolean;
  http_status: number | null;
  latency_ms: number;
  error: string | null;
}

async function probeUrl(url: string, timeoutMs = 5000): Promise<LiveProbeResult> {
  const start = Date.now();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      method: "GET",
      signal: controller.signal,
      headers: {
        "User-Agent": "OpenJobBoardHealthCheck/1.0",
        Accept: "application/json, application/xml, text/plain, */*",
      },
    });
    // Drain/cancel body to avoid leaking sockets
    try {
      await res.body?.cancel();
    } catch {
      // ignore
    }
    const latency = Date.now() - start;
    // USAJobs returns 401 without API key, which still proves the endpoint is reachable
    const reachable = (res.status >= 200 && res.status < 400) || (url.includes("usajobs.gov") && res.status === 401);
    return {
      reachable,
      http_status: res.status,
      latency_ms: latency,
      error: reachable ? null : `HTTP ${res.status}`,
    };
  } catch (err) {
    return {
      reachable: false,
      http_status: null,
      latency_ms: Date.now() - start,
      error: err instanceof Error ? err.message : String(err),
    };
  } finally {
    clearTimeout(timer);
  }
}

healthRoute.get("/", async (c) => {
  const db = c.get("db");
  const [ping, latestRun] = await Promise.all([
    db.execute("SELECT COUNT(*) AS active_jobs FROM jobs WHERE is_active = 1"),
    db.execute(
      "SELECT run_type, finished_at, status FROM ingestion_runs WHERE status = 'completed' ORDER BY finished_at DESC LIMIT 1"
    ),
  ]);

  const activeJobs = Number(ping.rows[0]?.active_jobs ?? 0);
  const lastSync = latestRun.rows[0]
    ? {
        run_type: String(latestRun.rows[0].run_type),
        finished_at: latestRun.rows[0].finished_at ? String(latestRun.rows[0].finished_at) : null,
      }
    : null;

  return c.json({
    status: "ok",
    active_jobs: activeJobs,
    last_sync: lastSync,
    timestamp: new Date().toISOString(),
  });
});

healthRoute.get("/sources", cacheControl(60, 180), async (c) => {
  const db = c.get("db");
  const shouldProbe = c.req.query("probe") === "true";
  const filterSource = c.req.query("source")?.trim().toLowerCase() || null;
  const nowMs = Date.now();

  const [boardsRes, jobsRes, latestFeedRunRes] = await Promise.all([
    db.execute(`
      SELECT
        ats,
        COUNT(*) AS total_boards,
        SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active_boards,
        SUM(CASE WHEN status = 'dead' THEN 1 ELSE 0 END) AS dead_boards,
        SUM(CASE WHEN last_error IS NOT NULL AND status = 'active' THEN 1 ELSE 0 END) AS boards_with_errors,
        MAX(last_synced_at) AS last_synced_at
      FROM boards
      GROUP BY ats
    `),
    db.execute(`
      SELECT
        source,
        source_type,
        COUNT(*) AS active_jobs,
        MAX(last_seen_at) AS last_seen_at
      FROM jobs
      WHERE is_active = 1
      GROUP BY source, source_type
    `),
    db.execute(`
      SELECT details_json, finished_at, status
      FROM ingestion_runs
      WHERE run_type = 'feed'
      ORDER BY started_at DESC
      LIMIT 1
    `),
  ]);

  const boardMap = new Map<
    string,
    {
      total_boards: number;
      active_boards: number;
      dead_boards: number;
      boards_with_errors: number;
      last_synced_at: string | null;
    }
  >();
  for (const r of boardsRes.rows) {
    boardMap.set(String(r.ats), {
      total_boards: Number(r.total_boards ?? 0),
      active_boards: Number(r.active_boards ?? 0),
      dead_boards: Number(r.dead_boards ?? 0),
      boards_with_errors: Number(r.boards_with_errors ?? 0),
      last_synced_at: r.last_synced_at ? String(r.last_synced_at) : null,
    });
  }

  const jobMap = new Map<string, { active_jobs: number; last_seen_at: string | null }>();
  for (const r of jobsRes.rows) {
    jobMap.set(`${String(r.source_type)}:${String(r.source)}`, {
      active_jobs: Number(r.active_jobs ?? 0),
      last_seen_at: r.last_seen_at ? String(r.last_seen_at) : null,
    });
  }

  let feedRunDetails: Record<string, { fetched?: number; upserted?: number; error?: string }> = {};
  const feedRunRow = latestFeedRunRes.rows[0];
  if (feedRunRow?.details_json) {
    try {
      const parsed = JSON.parse(String(feedRunRow.details_json));
      if (parsed && typeof parsed.feeds === "object") {
        feedRunDetails = parsed.feeds;
      }
    } catch {
      // ignore malformed JSON
    }
  }

  const atsList = filterSource
    ? ALL_ATS_SOURCES.filter((s) => s === filterSource)
    : [...ALL_ATS_SOURCES];

  const feedList = filterSource
    ? ALL_FEED_SOURCES.filter((s) => s === filterSource)
    : [...ALL_FEED_SOURCES];

  // Optional live HTTP probe for feeds
  const probeResults = new Map<string, LiveProbeResult>();
  if (shouldProbe && feedList.length > 0) {
    const entries = await Promise.all(
      feedList.map(async (name) => [name, await probeUrl(FEED_PROBE_URLS[name])] as const)
    );
    for (const [name, res] of entries) {
      probeResults.set(name, res);
    }
  }

  const atsHealth = atsList.map((ats) => {
    const b = boardMap.get(ats);
    const j = jobMap.get(`ats:${ats}`);
    const totalBoards = b?.total_boards ?? 0;
    const activeBoards = b?.active_boards ?? 0;
    const deadBoards = b?.dead_boards ?? 0;
    const boardsWithErrors = b?.boards_with_errors ?? 0;
    const lastSyncedAt = b?.last_synced_at ?? null;
    const activeJobs = j?.active_jobs ?? 0;

    let status: "healthy" | "degraded" | "uninitialized" = "uninitialized";
    if (totalBoards > 0) {
      const isStale = !lastSyncedAt || nowMs - Date.parse(lastSyncedAt) > STALE_THRESHOLD_MS;
      const highErrorRate = activeBoards > 0 && boardsWithErrors / activeBoards > 0.5;
      status = isStale || highErrorRate || activeBoards === 0 ? "degraded" : "healthy";
    }

    return {
      source: ats,
      source_type: "ats" as const,
      status,
      active_jobs: activeJobs,
      total_boards: totalBoards,
      active_boards: activeBoards,
      dead_boards: deadBoards,
      boards_with_errors: boardsWithErrors,
      last_synced_at: lastSyncedAt,
    };
  });

  const feedHealth = feedList.map((feed) => {
    const j = jobMap.get(`feed:${feed}`);
    const runInfo = feedRunDetails[feed];
    const activeJobs = j?.active_jobs ?? 0;
    const lastSeenAt = j?.last_seen_at ?? null;
    const lastError = runInfo?.error ?? null;
    const probe = probeResults.get(feed) ?? null;

    let status: "healthy" | "degraded" | "uninitialized" = "uninitialized";
    if (probe && !probe.reachable) {
      status = "degraded";
    } else if (lastError) {
      status = "degraded";
    } else if (activeJobs > 0 || runInfo) {
      const isStale = lastSeenAt ? nowMs - Date.parse(lastSeenAt) > STALE_THRESHOLD_MS : false;
      status = isStale ? "degraded" : "healthy";
    } else if (probe && probe.reachable) {
      status = "healthy";
    }

    return {
      source: feed,
      source_type: "feed" as const,
      status,
      active_jobs: activeJobs,
      last_seen_at: lastSeenAt,
      last_error: lastError,
      ...(probe ? { live_probe: probe } : {}),
    };
  });

  const allSources = [...atsHealth, ...feedHealth];
  const healthyCount = allSources.filter((s) => s.status === "healthy").length;
  const degradedCount = allSources.filter((s) => s.status === "degraded").length;
  const uninitializedCount = allSources.filter((s) => s.status === "uninitialized").length;

  const overallStatus =
    degradedCount > 0 ? "degraded" : healthyCount > 0 ? "healthy" : "uninitialized";

  return c.json({
    status: overallStatus,
    checked_at: new Date().toISOString(),
    probed: shouldProbe,
    summary: {
      total_sources: allSources.length,
      healthy: healthyCount,
      degraded: degradedCount,
      uninitialized: uninitializedCount,
    },
    sources: allSources,
  });
});
