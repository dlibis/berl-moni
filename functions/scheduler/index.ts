// Neon authenticates trigger invocations by stripping client-supplied X-Neon-* headers.
export default {
  async fetch(request: Request): Promise<Response> {
    if (request.method !== "POST") return new Response(null, { status: 405 });
    if (!request.headers.get("X-Neon-Trigger-Invocation-Id")) {
      return new Response(null, { status: 403 });
    }
    const secret = process.env.SCHEDULER_SECRET;
    const url = process.env.SCHEDULER_TICK_URL;
    if (!secret || !url) return new Response(null, { status: 503 });
    try {
      if (new URL(url).protocol !== "https:") return new Response(null, { status: 503 });
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${secret}` },
        signal: AbortSignal.timeout(20_000),
        redirect: "error",
      });
      // Do not log response bodies or URLs, which may contain deployment details.
      console.log(`scheduler tick HTTP ${response.status}`);
      if (!response.ok) return new Response(null, { status: 503 });
      const body = await response.json();
      const ok = ["idle", "dispatched", "already_dispatched"].includes(body?.status);
      if (ok) console.log(`scheduler tick ${body.status}`);
      return new Response(null, { status: ok ? 204 : 503 });
    } catch {
      console.warn("scheduler tick request failed");
      return new Response(null, { status: 503 });
    }
  },
};
