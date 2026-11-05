/**
 * PS5 Dashboard - Historical Index Client Tests.
 *
 * Verify MQTT subscription handling, retained index
 * validation, connection replacement, and disposal.
 *
 * All tests are isolated from Home Assistant and MQTT.
 */

import assert from "node:assert/strict";
import test from "node:test";

import {
  PS5HistoryIndexClient,
  validateHistoryIndex,
} from "../services/ps5-history-index-client.js";

/**
 * Create a valid index ending in the current local month.
 *
 * @returns {object} Complete historical index.
 */
function createIndex() {
  const now = new Date();

  const currentMonth =
    now.getFullYear() * 12 + now.getMonth();

  const months = [];

  for (let offset = -35; offset <= 0; offset++) {
    const absolute = currentMonth + offset;

    const year = Math.floor(absolute / 12);
    const month = absolute % 12 + 1;

    months.push({
      month: `${year}-${String(month).padStart(2, "0")}`,
      has_gaming: offset === -10 || offset === 0,
    });
  }

  return {
    schema_version: 1,
    month_count: 36,
    generated_at: new Date().toISOString(),
    months,
  };
}

/**
 * Create a simulated Home Assistant connection.
 *
 * @returns {object} Connection fixture and diagnostics.
 */
function createHass() {
  const subscriptions = [];
  const unsubscribed = [];

  const connection = {
    async subscribeMessage(callback, options) {
      const subscription = { callback, options };

      subscriptions.push(subscription);

      return () => {
        unsubscribed.push(subscription);
      };
    },
  };

  return {
    hass: { connection },
    subscriptions,
    unsubscribed,
  };
}

test("accepts a valid 36-month index", () => {
  const result = validateHistoryIndex(createIndex());

  assert.equal(result.index.month_count, 36);
  assert.equal(result.gamingPeriods.length, 2);
});

test("rejects a stale calendar window", () => {
  const index = createIndex();

  index.months[index.months.length - 1].month = "2020-01";

  assert.throws(
    () => validateHistoryIndex(index),
  );
});

test("subscribes to the dedicated MQTT topic", async () => {
  const fixture = createHass();

  const client = new PS5HistoryIndexClient(
    fixture.hass,
    () => {},
  );

  await client.connect();

  assert.equal(fixture.subscriptions.length, 1);

  assert.deepEqual(
    fixture.subscriptions[0].options,
    {
      type: "mqtt/subscribe",
      topic: "ps5-monitor/history/index",
      qos: 1,
    },
  );

  client.dispose();
});

test("prevents duplicate subscriptions", async () => {
  const fixture = createHass();

  const client = new PS5HistoryIndexClient(
    fixture.hass,
    () => {},
  );

  await Promise.all([
    client.connect(),
    client.connect(),
  ]);

  assert.equal(fixture.subscriptions.length, 1);

  client.dispose();
});

test("delivers validated MQTT index updates", async () => {
  const fixture = createHass();
  const updates = [];

  const client = new PS5HistoryIndexClient(
    fixture.hass,
    (value) => updates.push(value),
  );

  await client.connect();

  fixture.subscriptions[0].callback({
    topic: "ps5-monitor/history/index",
    payload: JSON.stringify(createIndex()),
  });

  assert.equal(updates.length, 1);
  assert.equal(updates[0].gamingPeriods.length, 2);

  client.dispose();
});

test("ignores unrelated MQTT topics", async () => {
  const fixture = createHass();
  const updates = [];

  const client = new PS5HistoryIndexClient(
    fixture.hass,
    (value) => updates.push(value),
  );

  await client.connect();

  fixture.subscriptions[0].callback({
    topic: "ps5-monitor/history/response",
    payload: JSON.stringify(createIndex()),
  });

  assert.equal(updates.length, 0);

  client.dispose();
});

test("releases subscriptions after connection replacement", async () => {
  const original = createHass();
  const replacement = createHass();

  const client = new PS5HistoryIndexClient(
    original.hass,
    () => {},
  );

  await client.connect();

  client.updateHass(replacement.hass);

  assert.equal(original.unsubscribed.length, 1);

  await client.connect();

  assert.equal(replacement.subscriptions.length, 1);

  client.dispose();
});

test("dispose prevents future updates", async () => {
  const fixture = createHass();
  const updates = [];

  const client = new PS5HistoryIndexClient(
    fixture.hass,
    (value) => updates.push(value),
  );

  await client.connect();

  const callback = fixture.subscriptions[0].callback;

  client.dispose();

  callback({
    topic: "ps5-monitor/history/index",
    payload: JSON.stringify(createIndex()),
  });

  assert.equal(updates.length, 0);
  assert.equal(fixture.unsubscribed.length, 1);
});

test("rejects a future generation timestamp", () => {
  const index = createIndex();

  index.generated_at = new Date(
    Date.now() + 3600000,
  ).toISOString();

  assert.throws(
    () => validateHistoryIndex(index),
    /future/,
  );
});

test("releases a subscription completed after connection replacement", async () => {
  /**
   * A pending subscription must not survive a connection
   * replacement, even when the old connection resolves later.
   */

  let resolveSubscription;
  let unsubscribeCount = 0;

  const originalConnection = {
    subscribeMessage() {
      return new Promise((resolve) => {
        resolveSubscription = resolve;
      });
    },
  };

  const replacement = createHass();

  const client = new PS5HistoryIndexClient(
    { connection: originalConnection },
    () => {},
  );

  const pending = client.connect();

  client.updateHass(replacement.hass);

  resolveSubscription(() => {
    unsubscribeCount += 1;
  });

  await assert.rejects(
    pending,
    /connection was replaced/,
  );

  assert.equal(unsubscribeCount, 1);
  assert.equal(client.unsubscribe, null);

  await client.connect();

  assert.equal(replacement.subscriptions.length, 1);

  client.dispose();
});

test("rejects an index from a previous calendar month", () => {
  /**
   * A retained index must not be accepted after the
   * calendar window has advanced to a new month.
   */

  const index = createIndex();

  const previousMonth = index.months.at(-2).month;

  index.months.pop();

  const firstMonth = index.months[0].month;
  const [year, month] = firstMonth.split("-").map(Number);

  const absolute = year * 12 + month - 2;
  const previousYear = Math.floor(absolute / 12);
  const previousNumber = absolute % 12 + 1;

  index.months.unshift({
    month: `${previousYear}-${String(previousNumber).padStart(2, "0")}`,
    has_gaming: false,
  });

  assert.equal(index.months.at(-1).month, previousMonth);
  assert.equal(index.months.length, 36);

  assert.throws(
    () => validateHistoryIndex(index),
    /current month/,
  );
});
