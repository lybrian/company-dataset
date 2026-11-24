import { Hono } from "hono";
import type { InValue } from "@libsql/client";
import { z } from "zod";
import { parseTagsJson } from "../db.js";
import { cacheControl } from "../middleware/cache.js";
import type { AppEnv } from "../types.js";

export const companiesRoute = new Hono<AppEnv>();

const listCompaniesSchema = z.object({
  q: z.string().trim().max(100).optional(),
  ats: z.string().trim().max(40).optional(),
  page: z.coerce.number().int().min(1).max(1000).default(1),
  limit: z.coerce.number().int().min(1).max(100).default(25),
});

const companyJobsSchema = z.object({
  page: z.coerce.number().int().min(1).max(1000).default(1),
  limit: z.coerce.number().int().min(1).max(100).default(25),
});

companiesRoute.get("/", cacheControl(120, 600), async (c) => {
  const parsed = listCompaniesSchema.safeParse(c.req.query());
  if (!parsed.success) {
    return c.json(
      { error: { code: "INVALID_QUERY", message: "Invalid query parameters", details: parsed.error.flatten().fieldErrors } },
      400
    );
  }

  const { q, ats, page, limit } = parsed.data;
  const db = c.get("db");
  const where: string[] = ["j.is_active = 1"];
  const args: InValue[] = [];

  if (q) {
    where.push("LOWER(c.name) LIKE ?");
    args.push(`%${q.toLowerCase()}%`);
  }
  if (ats) {
    where.push("c.ats = ?");
    args.push(ats.toLowerCase());
  }

  const whereSql = where.join(" AND ");
  const offset = (page - 1) * limit;

  const [countRes, rowsRes] = await Promise.all([
    db.execute({
      sql: `
        SELECT COUNT(DISTINCT c.id) AS total
        FROM companies c
        JOIN jobs j ON j.company_slug = c.slug
        WHERE ${whereSql}
      `,
      args,
    }),
    db.execute({
      sql: `
        SELECT c.slug, c.name, c.website_url, c.logo_url, c.description, c.ats,
               COUNT(j.id) AS active_jobs_count,
               MAX(j.posted_at) AS latest_job_at
        FROM companies c
        JOIN jobs j ON j.company_slug = c.slug
        WHERE ${whereSql}
        GROUP BY c.id
        ORDER BY active_jobs_count DESC, c.name ASC
        LIMIT ? OFFSET ?
      `,
      args: [...args, limit, offset],
    }),
  ]);

  const total = Number(countRes.rows[0]?.total ?? 0);
  const totalPages = Math.max(1, Math.ceil(total / limit));

  return c.json({
    data: rowsRes.rows.map((r) => ({
      slug: String(r.slug),
      name: String(r.name),
      website_url: r.website_url ? String(r.website_url) : null,
      logo_url: r.logo_url ? String(r.logo_url) : null,
      description: r.description ? String(r.description) : null,
      ats: r.ats ? String(r.ats) : null,
      active_jobs_count: Number(r.active_jobs_count ?? 0),
      latest_job_at: r.latest_job_at ? String(r.latest_job_at) : null,
    })),
    pagination: {
      page,
      limit,
      total,
      total_pages: totalPages,
      has_next: page < totalPages,
    },
  });
});

companiesRoute.get("/:slug", cacheControl(120, 600), async (c) => {
  const slug = c.req.param("slug").toLowerCase();
  const parsed = companyJobsSchema.safeParse(c.req.query());
  if (!parsed.success) {
    return c.json(
      { error: { code: "INVALID_QUERY", message: "Invalid pagination parameters" } },
      400
    );
  }
  const { page, limit } = parsed.data;
  const offset = (page - 1) * limit;
  const db = c.get("db");

  const companyRes = await db.execute({
    sql: "SELECT slug, name, website_url, logo_url, description, ats, ats_code FROM companies WHERE slug = ? LIMIT 1",
    args: [slug],
  });
  const comp = companyRes.rows[0];
  if (!comp) {
    return c.json(
      { error: { code: "NOT_FOUND", message: `Company '${slug}' not found` } },
      404
    );
  }

  const [countRes, jobsRes] = await Promise.all([
    db.execute({
      sql: "SELECT COUNT(*) AS total FROM jobs WHERE company_slug = ? AND is_active = 1",
      args: [slug],
    }),
    db.execute({
      sql: `
        SELECT id, source_type, source, title, apply_url, location, country,
               remote_type, employment_type, department, seniority, tags_json,
               salary_min, salary_max, salary_currency, salary_period, posted_at
        FROM jobs
        WHERE company_slug = ? AND is_active = 1
        ORDER BY posted_at DESC
        LIMIT ? OFFSET ?
      `,
      args: [slug, limit, offset],
    }),
  ]);

  const total = Number(countRes.rows[0]?.total ?? 0);
  const totalPages = Math.max(1, Math.ceil(total / limit));

  return c.json({
    data: {
      slug: String(comp.slug),
      name: String(comp.name),
      website_url: comp.website_url ? String(comp.website_url) : null,
      logo_url: comp.logo_url ? String(comp.logo_url) : null,
      description: comp.description ? String(comp.description) : null,
      ats: comp.ats ? String(comp.ats) : null,
      active_jobs_count: total,
      jobs: jobsRes.rows.map((r) => ({
        id: String(r.id),
        source_type: String(r.source_type),
        source: String(r.source),
        title: String(r.title),
        apply_url: String(r.apply_url),
        location: String(r.location ?? ""),
        country: r.country ? String(r.country) : null,
        remote_type: String(r.remote_type),
        employment_type: String(r.employment_type),
        department: r.department ? String(r.department) : null,
        seniority: r.seniority ? String(r.seniority) : null,
        tags: parseTagsJson(r.tags_json),
        salary:
          r.salary_min != null || r.salary_max != null
            ? {
                min: r.salary_min != null ? Number(r.salary_min) : null,
                max: r.salary_max != null ? Number(r.salary_max) : null,
                currency: r.salary_currency ? String(r.salary_currency) : null,
                period: r.salary_period ? String(r.salary_period) : null,
              }
            : null,
        posted_at: String(r.posted_at),
      })),
    },
    pagination: {
      page,
      limit,
      total,
      total_pages: totalPages,
      has_next: page < totalPages,
    },
  });
});
