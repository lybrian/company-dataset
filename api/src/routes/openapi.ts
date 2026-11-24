import { Hono } from "hono";
import { cacheControl } from "../middleware/cache.js";
import type { AppEnv } from "../types.js";

export const openapiRoute = new Hono<AppEnv>();

const OPENAPI_SPEC = {
  openapi: "3.1.0",
  info: {
    title: "Job Board Platform API",
    version: "1.0.0",
    description:
      "Public read-only REST API backed by Turso (libSQL) serving aggregated job postings from 17 ATS platforms and 10+ direct job feeds.",
  },
  paths: {
    "/api/v1/health": {
      get: {
        summary: "Health check and latest sync metadata",
        responses: { "200": { description: "Healthy" } },
      },
    },
    "/api/v1/health/sources": {
      get: {
        summary: "Per-source health check across all 17 ATS platforms and 11 direct job feeds",
        parameters: [
          { name: "probe", in: "query", schema: { type: "boolean", default: false }, description: "When true, performs live HTTP reachability and latency checks against feed endpoints" },
          { name: "source", in: "query", schema: { type: "string" }, description: "Optional single source name filter (e.g. greenhouse, remoteok)" },
        ],
        responses: { "200": { description: "Per-source health summary and status list" } },
      },
    },
    "/api/v1/jobs": {
      get: {
        summary: "Search and filter active job postings",
        parameters: [
          { name: "q", in: "query", schema: { type: "string" }, description: "Full-text search (FTS5)" },
          { name: "remote", in: "query", schema: { type: "string", enum: ["remote", "hybrid", "onsite", "unknown"] } },
          {
            name: "employment_type",
            in: "query",
            schema: { type: "string", enum: ["full_time", "part_time", "contract", "internship", "freelance", "unknown"] },
          },
          { name: "source", in: "query", schema: { type: "string" }, description: "ATS or feed name (e.g. greenhouse, remoteok)" },
          { name: "source_type", in: "query", schema: { type: "string", enum: ["ats", "feed"] } },
          { name: "company", in: "query", schema: { type: "string" } },
          { name: "country", in: "query", schema: { type: "string" }, description: "ISO-2 country code (e.g. US, GB, DE)" },
          { name: "location", in: "query", schema: { type: "string" } },
          { name: "tag", in: "query", schema: { type: "string" } },
          { name: "salary_min", in: "query", schema: { type: "integer" } },
          { name: "posted_since", in: "query", schema: { type: "string" }, description: "24h, 7d, 30d, or ISO-8601 date" },
          { name: "sort", in: "query", schema: { type: "string", enum: ["newest", "salary", "relevance"] } },
          { name: "page", in: "query", schema: { type: "integer", default: 1 } },
          { name: "limit", in: "query", schema: { type: "integer", default: 25, maximum: 100 } },
        ],
        responses: { "200": { description: "Paginated job summaries" } },
      },
    },
    "/api/v1/jobs/{id}": {
      get: {
        summary: "Get full job posting details",
        parameters: [{ name: "id", in: "path", required: true, schema: { type: "string" } }],
        responses: {
          "200": { description: "Job detail" },
          "404": { description: "Not found" },
        },
      },
    },
    "/api/v1/companies": {
      get: {
        summary: "List companies with active job postings",
        parameters: [
          { name: "q", in: "query", schema: { type: "string" } },
          { name: "ats", in: "query", schema: { type: "string" } },
          { name: "page", in: "query", schema: { type: "integer", default: 1 } },
          { name: "limit", in: "query", schema: { type: "integer", default: 25 } },
        ],
        responses: { "200": { description: "Paginated companies" } },
      },
    },
    "/api/v1/companies/{slug}": {
      get: {
        summary: "Get company profile and its active jobs",
        parameters: [{ name: "slug", in: "path", required: true, schema: { type: "string" } }],
        responses: {
          "200": { description: "Company detail and jobs" },
          "404": { description: "Not found" },
        },
      },
    },
    "/api/v1/filters": {
      get: {
        summary: "Get dynamic facet counts for frontend filter controls",
        responses: { "200": { description: "Facet counts" } },
      },
    },
    "/api/v1/stats": {
      get: {
        summary: "Get job board statistics and recent ingestion runs",
        responses: { "200": { description: "Board metrics" } },
      },
    },
  },
};

openapiRoute.get("/", cacheControl(3600, 86400), (c) => c.json(OPENAPI_SPEC));
