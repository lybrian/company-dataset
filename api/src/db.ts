import { createClient, type Client } from "@libsql/client";

const clientCache = new Map<string, Client>();

export function getDbClient(url: string, authToken?: string): Client {
  const key = `${url}::${authToken ?? ""}`;
  const existing = clientCache.get(key);
  if (existing) {
    return existing;
  }
  const client = createClient({
    url,
    authToken: authToken || undefined,
  });
  clientCache.set(key, client);
  return client;
}

export function clearDbClientCache(): void {
  for (const client of clientCache.values()) {
    client.close();
  }
  clientCache.clear();
}

export function parseTagsJson(raw: unknown): string[] {
  if (typeof raw !== "string" || !raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === "string") : [];
  } catch {
    return [];
  }
}

export function sanitizeFtsQuery(raw: string): string {
  const tokens = raw
    .trim()
    .replace(/["'()*^:+-]/g, " ")
    .split(/\s+/)
    .filter((t) => t.length >= 2)
    .slice(0, 8);
  if (tokens.length === 0) return "";
  return tokens.map((t) => `"${t}"*`).join(" AND ");
}
