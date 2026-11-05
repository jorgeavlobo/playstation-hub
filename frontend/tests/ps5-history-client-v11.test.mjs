/**
 * PS5 Dashboard - Historical Client v1.1 Tests.
 *
 * Verify subscription lifecycle, request cancellation,
 * concurrent requests, connection replacement, and cleanup.
 *
 * All Home Assistant dependencies are simulated.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(
  new URL("../services/ps5-history-client.js", import.meta.url),
  "utf8",
);

const moduleUrl = `data:text/javascript;base64,${
  Buffer.from(source).toString("base64")
}`;

const { PS5HistoryClient } = await import(moduleUrl);

/**
 * Create a controllable Home Assistant simulation.
 */
function createFakeHass() {
  const state = {
    callback: null,
    subscribeCount: 0,
    unsubscribeCount: 0,
    publications: [],
  };

  const hass = {
    connection: {
      async subscribeMessage(callback) {
        state.callback = callback;
        state.subscribeCount += 1;

        return () => {
          state.unsubscribeCount += 1;
        };
      },
    },

    async callService(domain, service, data) {
      assert.equal(domain, "mqtt");
      assert.equal(service, "publish");

      state.publications.push(data);
    },
  };

  return { hass, state };
}

/**
 * Wait until a condition becomes true.
 *
 * Avoid assuming a fixed amount of scheduling latency.
 */
async function waitFor(predicate, timeoutMs = 5000) {
  const started = Date.now();

  while (!predicate()) {
    if (Date.now() - started > timeoutMs) {
      throw new Error("Test condition timed out.");
    }

    await new Promise((resolve) => setTimeout(resolve, 10));
  }
}

/**
 * Construct a valid historical response.
 */
function makeResponse(requestId, period) {
  return {
    request_id: requestId,
    schema_version: 1,
    period,
    summary: {
      console_seconds: 3600,
      gaming_seconds: 3600,
      gaming_sessions: 1,
    },
    game_count: 1,
    games: [
      {
        title_id: "PPSA17221_00",
        title_name: "Minecraft",
        title_image: "https://example.com/minecraft.png",
        duration_seconds: 3600,
        session_count: 1,
      },
    ],
  };
}

/**
 * Deliver a response through the simulated MQTT subscription.
 */
function deliver(state, response) {
  state.callback({
    topic: "ps5-monitor/history/response",
    payload: JSON.stringify(response),
  });
}

test("reuses one MQTT subscription", async () => {
  const { hass, state } = createFakeHass();
  const client = new PS5HistoryClient(hass);

  const first = client.getMonth("2026-11");

  await waitFor(() => state.publications.length === 1);

  const firstRequest = JSON.parse(state.publications[0].payload);

  deliver(state, makeResponse(firstRequest.request_id, "2026-11"));

  await first;

  const second = client.getMonth("2026-10");

  await waitFor(() => state.publications.length === 2);

  const secondRequest = JSON.parse(state.publications[1].payload);

  deliver(state, makeResponse(secondRequest.request_id, "2026-10"));

  await second;

  assert.equal(state.subscribeCount, 1);

  client.dispose();

  assert.equal(state.unsubscribeCount, 1);
});

test("correlates concurrent requests", async () => {
  const { hass, state } = createFakeHass();
  const client = new PS5HistoryClient(hass);

  const november = client.getMonth("2026-11");
  const october = client.getMonth("2026-10");

  await waitFor(() => state.publications.length === 2);

  const requests = state.publications.map(
    (publication) => JSON.parse(publication.payload),
  );

  for (const request of [...requests].reverse()) {
    deliver(
      state,
      makeResponse(request.request_id, request.period),
    );
  }

  const results = await Promise.all([november, october]);

  assert.equal(results[0].period, "2026-11");
  assert.equal(results[1].period, "2026-10");

  client.dispose();
});

test("cancels an active request", async () => {
  const { hass, state } = createFakeHass();
  const client = new PS5HistoryClient(hass);

  const controller = new AbortController();

  const pending = client.getMonth("2026-11", {
    signal: controller.signal,
  });

  await waitFor(() => state.publications.length === 1);

  controller.abort();

  await assert.rejects(
    pending,
    (error) => error.name === "AbortError",
  );

  assert.equal(client.pendingRequests.size, 0);

  client.dispose();
});

test("rejects malformed matching responses", async () => {
  const { hass, state } = createFakeHass();
  const client = new PS5HistoryClient(hass);

  const pending = client.getMonth("2026-11");

  await waitFor(() => state.publications.length === 1);

  const request = JSON.parse(state.publications[0].payload);

  deliver(state, {
    request_id: request.request_id,
    schema_version: 999,
    period: "2026-11",
  });

  await assert.rejects(
    pending,
    /Unsupported historical schema version/,
  );

  client.dispose();
});

test("rejects pending requests on disposal", async () => {
  const { hass, state } = createFakeHass();
  const client = new PS5HistoryClient(hass);

  const pending = client.getMonth("2026-11");

  await waitFor(() => state.publications.length === 1);

  client.dispose();

  await assert.rejects(
    pending,
    /Home Assistant connection changed/,
  );

  assert.equal(state.unsubscribeCount, 1);
  assert.equal(client.pendingRequests.size, 0);
});
