import assert from "node:assert/strict";
import { test } from "node:test";
import scheduler from "./index.ts";

test("Neon scheduler authenticates triggers and forwards only to its configured endpoint", async (t) => {
  const oldSecret = process.env.SCHEDULER_SECRET;
  const oldUrl = process.env.SCHEDULER_TICK_URL;
  t.after(() => {
    if (oldSecret === undefined) delete process.env.SCHEDULER_SECRET;
    else process.env.SCHEDULER_SECRET = oldSecret;
    if (oldUrl === undefined) delete process.env.SCHEDULER_TICK_URL;
    else process.env.SCHEDULER_TICK_URL = oldUrl;
  });
  process.env.SCHEDULER_SECRET = "test-only-secret";
  process.env.SCHEDULER_TICK_URL = "https://example.com/api/internal/scheduler/tick";
  const calls = [];
  const fetchMock = t.mock.method(globalThis, "fetch", async (url, options) => {
    calls.push({ url, options });
    return Response.json({ status: "idle" });
  });
  const invoke = (method = "POST", headers = { "X-Neon-Trigger-Invocation-Id": "test" }) =>
    scheduler.fetch(new Request("https://function.example/", { method, headers }));

  assert.equal((await invoke("GET")).status, 405);
  assert.equal((await invoke("POST", {})).status, 403);
  delete process.env.SCHEDULER_SECRET;
  assert.equal((await invoke()).status, 503);
  process.env.SCHEDULER_SECRET = "test-only-secret";
  process.env.SCHEDULER_TICK_URL = "http://example.com/";
  assert.equal((await invoke()).status, 503);
  assert.equal(calls.length, 0);

  process.env.SCHEDULER_TICK_URL = "https://example.com/api/internal/scheduler/tick";
  assert.equal((await invoke()).status, 204);
  assert.equal(calls[0].url, process.env.SCHEDULER_TICK_URL);
  assert.equal(calls[0].options.headers.Authorization, "Bearer test-only-secret");
  assert.equal(calls[0].options.redirect, "error");
  assert.ok(calls[0].options.signal instanceof AbortSignal);

  fetchMock.mock.mockImplementation(async () => new Response("<html>Wrong route</html>"));
  assert.equal((await invoke()).status, 503);

  fetchMock.mock.mockImplementation(async () => new Response(null, { status: 503 }));
  assert.equal((await invoke()).status, 503);
  fetchMock.mock.mockImplementation(async () => { throw new DOMException("timeout", "TimeoutError"); });
  assert.equal((await invoke()).status, 503);
});
