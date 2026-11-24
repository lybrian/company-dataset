import { Hono } from "hono";
import { cors } from "hono/cors";
import { secureHeaders } from "hono/secure-headers";
import type { Client } from "@libsql/client";
import { getDbClient } from "./db.js";
import { companiesRoute } from "./routes/companies.js";
import { filtersRoute } from "./routes/filters.js";
import { healthRoute } from "./routes/health.js";
import { jobsRoute } from "./routes/jobs.js";
import { openapiRoute } from "./routes/openapi.js";
import { statsRoute } from "./routes/stats.js";
import type { AppEnv } from "./types.js";

export interface CreateAppOptions {
  db?: Client;
}

export function createApp(options: CreateAppOptions = {}) {
  const app = new Hono<AppEnv>();

  app.use("*", secureHeaders());
  app.use(
    "*",
    cors({
      origin: (origin, c) => {
        const allowed = String(c.env?.CORS_ORIGINS ?? process.env.CORS_ORIGINS ?? "*").trim();
        if (allowed === "*") return "*";
        const list = allowed.split(",").map((s: string) => s.trim());
        return list.includes(origin) ? origin : list[0] ?? "";
      },
      allowMethods: ["GET", "OPTIONS"],
      allowHeaders: ["Content-Type", "Accept"],
      maxAge: 86400,
    })
  );

  // Inject libSQL / Turso client into request context
  app.use("/api/*", async (c, next) => {
    if (options.db) {
      c.set("db", options.db);
    } else {
      const url = c.env?.TURSO_DATABASE_URL ?? process.env.TURSO_DATABASE_URL;
      const token = c.env?.TURSO_AUTH_TOKEN ?? process.env.TURSO_AUTH_TOKEN;
      if (!url) {
        return c.json(
          { error: { code: "CONFIG_ERROR", message: "TURSO_DATABASE_URL is not configured" } },
          500
        );
      }
      c.set("db", getDbClient(url, token));
    }
    await next();
  });

  app.get("/", (c) =>
    c.json({
      name: "Job Board Platform API",
      version: "1.0.0",
      docs: "/api/v1/openapi.json",
      endpoints: {
        health: "/api/v1/health",
        health_sources: "/api/v1/health/sources",
        jobs: "/api/v1/jobs",
        companies: "/api/v1/companies",
        filters: "/api/v1/filters",
        stats: "/api/v1/stats",
      },
    })
  );

  app.route("/api/v1/health", healthRoute);
  app.route("/api/v1/jobs", jobsRoute);
  app.route("/api/v1/companies", companiesRoute);
  app.route("/api/v1/filters", filtersRoute);
  app.route("/api/v1/stats", statsRoute);
  app.route("/api/v1/openapi.json", openapiRoute);

  app.notFound((c) =>
    c.json({ error: { code: "NOT_FOUND", message: `Route ${c.req.path} not found` } }, 404)
  );

  app.onError((err, c) => {
    console.error("[api] unhandled error:", err);
    return c.json(
      { error: { code: "INTERNAL_ERROR", message: "An unexpected error occurred" } },
      500
    );
  });

  return app;
}
