import { Hono } from "hono";
import { cacheControl } from "../middleware/cache.js";
import type { AppEnv } from "../types.js";

export const filtersRoute = new Hono<AppEnv>();

filtersRoute.get("/", cacheControl(300, 900), async (c) => {
  const db = c.get("db");

  const [remoteRes, empRes, countryRes, sourceRes, deptRes] = await Promise.all([
    db.execute(
      "SELECT remote_type AS value, COUNT(*) AS count FROM jobs WHERE is_active = 1 GROUP BY remote_type ORDER BY count DESC"
    ),
    db.execute(
      "SELECT employment_type AS value, COUNT(*) AS count FROM jobs WHERE is_active = 1 GROUP BY employment_type ORDER BY count DESC"
    ),
    db.execute(
      "SELECT country AS value, COUNT(*) AS count FROM jobs WHERE is_active = 1 AND country IS NOT NULL GROUP BY country ORDER BY count DESC LIMIT 40"
    ),
    db.execute(
      "SELECT source AS value, source_type, COUNT(*) AS count FROM jobs WHERE is_active = 1 GROUP BY source, source_type ORDER BY count DESC"
    ),
    db.execute(
      "SELECT department AS value, COUNT(*) AS count FROM jobs WHERE is_active = 1 AND department IS NOT NULL AND department != '' GROUP BY department ORDER BY count DESC LIMIT 30"
    ),
  ]);

  return c.json({
    data: {
      remote_types: remoteRes.rows.map((r) => ({ value: String(r.value), count: Number(r.count) })),
      employment_types: empRes.rows.map((r) => ({ value: String(r.value), count: Number(r.count) })),
      countries: countryRes.rows.map((r) => ({ value: String(r.value), count: Number(r.count) })),
      sources: sourceRes.rows.map((r) => ({
        value: String(r.value),
        source_type: String(r.source_type),
        count: Number(r.count),
      })),
      departments: deptRes.rows.map((r) => ({ value: String(r.value), count: Number(r.count) })),
    },
  });
});
