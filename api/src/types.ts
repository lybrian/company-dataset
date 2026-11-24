import type { Client } from "@libsql/client";

export interface AppBindings {
  TURSO_DATABASE_URL: string;
  TURSO_AUTH_TOKEN?: string;
  CORS_ORIGINS?: string;
}

export interface AppVariables {
  db: Client;
}

export interface AppEnv {
  Bindings: AppBindings;
  Variables: AppVariables;
}

export interface JobSummary {
  id: string;
  source_type: string;
  source: string;
  company_name: string;
  company_slug: string;
  company_logo: string | null;
  title: string;
  snippet: string;
  apply_url: string;
  source_url: string | null;
  location: string;
  country: string | null;
  remote_type: string;
  employment_type: string;
  department: string | null;
  seniority: string | null;
  tags: string[];
  salary: {
    min: number | null;
    max: number | null;
    currency: string | null;
    period: string | null;
  } | null;
  posted_at: string;
}

export interface JobDetail extends JobSummary {
  description_html: string | null;
  description_text: string;
  first_seen_at: string;
  last_seen_at: string;
}
