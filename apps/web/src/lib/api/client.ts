import type { components } from "./schema";
export type Profile = components["schemas"]["Profile"];
export type Job = components["schemas"]["JobRecord"];
export type Run = components["schemas"]["RunRecord"];
export type Approval = components["schemas"]["Approval"];
const base =
  (import.meta as unknown as { env: { VITE_API_URL?: string } }).env
    .VITE_API_URL || "";
export function authHeaders(): Record<string, string> {
  const t = localStorage.getItem("gigbid-token");
  return t ? { Authorization: `Bearer ${t}` } : {};
}
export async function api<T = Record<string, unknown>>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const r = await fetch(base + "/api" + path, {
    method,
    headers: {
      ...authHeaders(),
      ...(body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
    },
    body:
      body === undefined
        ? undefined
        : body instanceof FormData
          ? body
          : JSON.stringify(body),
  });
  if (!r.ok) {
    const data = await r
      .json()
      .catch(() => ({ detail: "Service unavailable" }));
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : `Request failed (${r.status})`,
    );
  }
  return r.json();
}
export async function watchRun(
  id: string,
  onState: (value: Run) => void,
  signal: AbortSignal,
) {
  const r = await fetch(base + `/api/runs/${id}/events`, {
    headers: authHeaders(),
    signal,
  });
  if (!r.ok) throw new Error("Cannot open progress stream");
  const reader = r.body!.getReader(),
    decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let end;
    while ((end = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      if (block.startsWith("event: state")) {
        const line = block.split("\n").find((x) => x.startsWith("data: "));
        if (line) onState(JSON.parse(line.slice(6)));
      }
    }
  }
}
