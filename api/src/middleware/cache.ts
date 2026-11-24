import type { MiddlewareHandler } from "hono";

export function cacheControl(maxAge: number, staleWhileRevalidate = 300): MiddlewareHandler {
  return async (c, next) => {
    await next();
    if (c.req.method === "GET" && c.res.status >= 200 && c.res.status < 300) {
      c.header(
        "Cache-Control",
        `public, max-age=${maxAge}, stale-while-revalidate=${staleWhileRevalidate}`
      );
    }
  };
}
