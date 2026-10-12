import type { Analysis, AnalyzeRequest, GeoResult } from "./types";

export class ApiError extends Error {}

const prettify = (key: string) => key.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

/** DRF returns strings, arrays, {detail} or nested field errors; reduce them all to one sentence. */
function flatten(body: unknown): string {
  if (typeof body === "string") return body;
  if (Array.isArray(body)) return body.map(flatten).join(" ");
  if (body && typeof body === "object") {
    const obj = body as Record<string, unknown>;
    if ("detail" in obj) return flatten(obj.detail);
    return Object.entries(obj)
      .map(([k, v]) => (k === "non_field_errors" ? flatten(v) : `${prettify(k)}: ${flatten(v)}`))
      .join(" ");
  }
  return "Unexpected error";
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const message = await res.json().then(flatten, () => `Request failed (${res.status})`);
    throw new ApiError(message);
  }
  return res.json() as Promise<T>;
}

export const api = {
  geocode: (q: string, signal: AbortSignal) =>
    request<GeoResult[]>(`/api/geocode?q=${encodeURIComponent(q)}`, { signal }),
  analyze: (body: AnalyzeRequest, signal: AbortSignal) =>
    request<Analysis>("/api/routes/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    }),
};
