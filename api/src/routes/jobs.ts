import { Hono } from "hono";
import type { InValue, Row } from "@libsql/client";
import { z } from "zod";
import { parseTagsJson, sanitizeFtsQuery } from "../db.js";
import { cacheControl } from "../middleware/cache.js";
import type { AppEnv, JobDetail, JobSummary } from "../types.js";

export const jobsRoute = new Hono<AppEnv>();

const listQuerySchema = z.object({
  q: z.string().trim().max(120).optional(),
  remote: z.enum(["remote", "hybrid", "onsite", "unknown"]).optional(),
  employment_type: z
    .enum(["full_time", "part_time", "contract", "internship", "freelance", "unknown"])
    .optional(),
  source: z.string().trim().max(40).optional(),
  source_type: z.enum(["ats", "feed"]).optional(),
  company: z.string().trim().max(100).optional(),
  country: z
    .string()
    .trim()
    .length(2)
    .transform((v) => v.toUpperCase())
    .optional(),
  location: z.string().trim().max(80).optional(),
  tag: z.string().trim().max(40).optional(),
  salary_min: z.coerce.number().int().min(0).max(10_000_000).optional(),
  posted_since: z.string().trim().max(40).optional(),
  sort: z.enum(["newest", "salary", "relevance"]).default("newest"),
  page: z.coerce.number().int().min(1).max(1000).default(1),
  limit: z.coerce.number().int().min(1).max(100).default(25),
});

function resolvePostedSince(raw?: string): string | null {
  if (!raw) return null;
  const now = Date.now();
  if (raw === "24h") return new Date(now - 24 * 3600 * 1000).toISOString();
  if (raw === "7d") return new Date(now - 7 * 24 * 3600 * 1000).toISOString();
  if (raw === "30d") return new Date(now - 30 * 24 * 3600 * 1000).toISOString();
  const parsed = Date.parse(raw);
  return Number.isNaN(parsed) ? null : new Date(parsed).toISOString();
}

function rowToJobSummary(row: Row): JobSummary {
  const salMin = row.salary_min != null ? Number(row.salary_min) : null;
  const salMax = row.salary_max != null ? Number(row.salary_max) : null;
  const desc = String(row.description_text ?? "");
  return {
    id: String(row.id),
    source_type: String(row.source_type),
    source: String(row.source),
    company_name: String(row.company_name),
    company_slug: String(row.company_slug),
    company_logo: row.company_logo ? String(row.company_logo) : null,
    title: String(row.title),
    snippet: desc.length > 260 ? `${desc.slice(0, 257)}...` : desc,
    apply_url: String(row.apply_url),
    source_url: row.source_url ? String(row.source_url) : null,
    location: String(row.location ?? ""),
    country: row.country ? String(row.country) : null,
    remote_type: String(row.remote_type),
    employment_type: String(row.employment_type),
    department: row.department ? String(row.department) : null,
    seniority: row.seniority ? String(row.seniority) : null,
    tags: parseTagsJson(row.tags_json),
    salary:
      salMin != null || salMax != null
        ? {
            min: salMin,
            max: salMax,
            currency: row.salary_currency ? String(row.salary_currency) : null,
            period: row.salary_period ? String(row.salary_period) : null,
          }
        : null,
    posted_at: String(row.posted_at),
  };
}

jobsRoute.get("/", cacheControl(60, 300), async (c) => {
  const parsed = listQuerySchema.safeParse(c.req.query());
  if (!parsed.success) {
    return c.json(
      {
        error: {
          code: "INVALID_QUERY",
          message: "Invalid query parameters",
          details: parsed.error.flatten().fieldErrors,
        },
      },
      400
    );
  }

  const params = parsed.data;
  const db = c.get("db");
  const ftsQuery = params.q ? sanitizeFtsQuery(params.q) : "";
  const useFts = ftsQuery.length > 0;

  const joins = useFts ? "JOIN jobs_fts ON jobs_fts.rowid = jobs.rowid" : "";
  const where: string[] = ["jobs.is_active = 1"];
  const args: InValue[] = [];

  if (useFts) {
    where.push("jobs_fts MATCH ?");
    args.push(ftsQuery);
  }
  if (params.remote) {
    where.push("jobs.remote_type = ?");
    args.push(params.remote);
  }
  if (params.employment_type) {
    where.push("jobs.employment_type = ?");
    args.push(params.employment_type);
  }
  if (params.source) {
    where.push("jobs.source = ?");
    args.push(params.source.toLowerCase());
  }
  if (params.source_type) {
    where.push("jobs.source_type = ?");
    args.push(params.source_type);
  }
  if (params.company) {
    where.push("(jobs.company_slug = ? OR LOWER(jobs.company_name) LIKE ?)");
    args.push(params.company.toLowerCase(), `%${params.company.toLowerCase()}%`);
  }
  if (params.country) {
    where.push("jobs.country = ?");
    args.push(params.country);
  }
  if (params.location) {
    where.push("LOWER(jobs.location) LIKE ?");
    args.push(`%${params.location.toLowerCase()}%`);
  }
  if (params.tag) {
    where.push("LOWER(jobs.tags_text) LIKE ?");
    args.push(`%${params.tag.toLowerCase()}%`);
  }
  if (params.salary_min != null) {
    where.push("COALESCE(jobs.salary_max, jobs.salary_min, 0) >= ?");
    args.push(params.salary_min);
  }
  const sinceIso = resolvePostedSince(params.posted_since);
  if (sinceIso) {
    where.push("jobs.posted_at >= ?");
    args.push(sinceIso);
  }

  const whereSql = where.join(" AND ");
  let orderSql = "jobs.posted_at DESC";
  if (params.sort === "salary") {
    orderSql = "COALESCE(jobs.salary_max, jobs.salary_min, 0) DESC, jobs.posted_at DESC";
  } else if (params.sort === "relevance" && useFts) {
    orderSql = "bm25(jobs_fts), jobs.posted_at DESC";
  }

  const offset = (params.page - 1) * params.limit;

  const [countRes, rowsRes] = await Promise.all([
    db.execute({
      sql: `SELECT COUNT(*) AS total FROM jobs ${joins} WHERE ${whereSql}`,
      args,
    }),
    db.execute({
      sql: `
        SELECT jobs.id, jobs.source_type, jobs.source, jobs.company_name, jobs.company_slug,
               jobs.company_logo, jobs.title, jobs.description_text, jobs.apply_url,
               jobs.source_url, jobs.location, jobs.country, jobs.remote_type,
               jobs.employment_type, jobs.department, jobs.seniority, jobs.tags_json,
               jobs.salary_min, jobs.salary_max, jobs.salary_currency, jobs.salary_period,
               jobs.posted_at
        FROM jobs
        ${joins}
        WHERE ${whereSql}
        ORDER BY ${orderSql}
        LIMIT ? OFFSET ?
      `,
      args: [...args, params.limit, offset],
    }),
  ]);

  const total = Number(countRes.rows[0]?.total ?? 0);
  const totalPages = Math.max(1, Math.ceil(total / params.limit));

  return c.json({
    data: rowsRes.rows.map(rowToJobSummary),
    pagination: {
      page: params.page,
      limit: params.limit,
      total,
      total_pages: totalPages,
      has_next: params.page < totalPages,
    },
  });
});

jobsRoute.get("/:id", cacheControl(120, 600), async (c) => {
  const id = c.req.param("id");
  const db = c.get("db");
  const res = await db.execute({
    sql: `
      SELECT id, source_type, source, company_name, company_slug, company_logo,
             title, description_html, description_text, apply_url, source_url,
             location, country, remote_type, employment_type, department, seniority,
             tags_json, salary_min, salary_max, salary_currency, salary_period,
             posted_at, first_seen_at, last_seen_at
      FROM jobs
      WHERE id = ? AND is_active = 1
      LIMIT 1
    `,
    args: [id],
  });

  const row = res.rows[0];
  if (!row) {
    return c.json(
      { error: { code: "NOT_FOUND", message: `Job '${id}' not found` } },
      404
    );
  }

  const base = rowToJobSummary(row);
  const detail: JobDetail = {
    ...base,
    description_html: row.description_html ? String(row.description_html) : null,
    description_text: String(row.description_text ?? ""),
    first_seen_at: String(row.first_seen_at),
    last_seen_at: String(row.last_seen_at),
  };

  return c.json({ data: detail });
});
