/**
 * PS5 Dashboard - Historical MQTT Client Tests.
 *
 * Run with Node.js 24 using the built-in test runner.
 *
 * These tests simulate the Home Assistant WebSocket interface.
 * They do not access a real MQTT broker or production database.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const moduleSource = await readFile(
  new URL("../services/ps5-history-client.js", import.meta.url),
  "utf8",
);

// Import the JavaScript source as an ES module without requiring
// changes to the Home Assistant frontend file structure.
const moduleUrl = `data:text/javascript;base64,${
  Buffer.from(moduleSource).toString("base64")
}`;

const { PS5HistoryClient } = await import(moduleUrl);

/**
 * Create a simulated Home Assistant environment.
 *
 * The fake MQTT subscription receives messages through a
 * callback supplied by the test.
 */
function createFakeHass() {
  const state = {
    callback: null,
    subscribed: false,
    unsubscribed: false,
    publications: [],
    subscriptionTopic: null,
  };

  const hass = {
    connection: {
      async subscribeMessage(callback, subscription) {
        state.callback = callback;
        state.subscribed = true;
        state.subscriptionTopic = subscription.topic;

        return () => {
          state.unsubscribed = true;
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

test("subscribes before publishing", async () => {
  const { hass, state } = createFakeHass();
  const client = new PS5HistoryClient(hass);

  const pending = client.getMonth("2026-11");

  // Allow the asynchronous subscription to complete.
  await new Promise((resolve) => setTimeout(resolve, 2100));

  assert.equal(state.subscribed, true);
  assert.equal(state.publications.length, 1);

  const request = JSON.parse(state.publications[0].payload);

  assert.equal(request.period, "2026-11");
  assert.match(request.request_id, /^ps5-/);

  state.callback({
    topic: "ps5-monitor/history/response",
    payload: JSON.stringify({
      request_id: request.request_id,
      period: "2026-11",
      schema_version: 1,
      summary: {
        console_seconds: 3600,
        gaming_seconds: 1800,
        gaming_sessions: 1,
      },
      game_count: 0,
      games: [],
    }),
  });

  const response = await pending;

  assert.equal(response.period, "2026-11");
  // The shared subscription remains active after a request.
  assert.equal(state.unsubscribed, false);

  // Disposal must release the MQTT subscription.
  client.dispose();

  assert.equal(state.unsubscribed, true);
});

test("ignores unrelated responses", async () => {
  const { hass, state } = createFakeHass();
  const client = new PS5HistoryClient(hass);

  const pending = client.getMonth("2026-11");

  await new Promise((resolve) => setTimeout(resolve, 2100));

  const request = JSON.parse(state.publications[0].payload);

  state.callback({
    topic: "ps5-monitor/history/response",
    payload: JSON.stringify({
      request_id: "another-request",
      period: "2026-11",
    }),
  });

  state.callback({
    topic: "ps5-monitor/history/response",
    payload: JSON.stringify({
      request_id: request.request_id,
      period: "2026-11",
      schema_version: 1,
      summary: {
        console_seconds: 3600,
        gaming_seconds: 1800,
        gaming_sessions: 1,
      },
      game_count: 0,
      games: [],
    }),
  });

  const response = await pending;

  assert.equal(response.request_id, request.request_id);
  // The shared subscription remains active after a request.
  assert.equal(state.unsubscribed, false);

  // Disposal must release the MQTT subscription.
  client.dispose();

  assert.equal(state.unsubscribed, true);
});

test("rejects invalid calendar periods", async () => {
  const { hass } = createFakeHass();
  const client = new PS5HistoryClient(hass);

  await assert.rejects(
    client.getMonth("2026-13"),
    /Invalid calendar period/,
  );

  await assert.rejects(
    client.getMonth("invalid"),
    /Invalid calendar period/,
  );
});
