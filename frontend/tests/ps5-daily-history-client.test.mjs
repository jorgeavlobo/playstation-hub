import test from "node:test";
import assert from "node:assert/strict";
import { PS5DailyHistoryClient, validateDailyHistory } from "../services/ps5-daily-history-client.js";

function fixture() {
  const state = { subscriptions: [], publications: [], unsubscriptions: 0 };
  const hass = {
    connection: {
      async subscribeMessage(callback, options) {
        state.subscriptions.push({ callback, options });
        return () => { state.unsubscriptions++; };
      },
    },
    async callService(domain, service, payload) {
      assert.equal(domain, "mqtt");
      assert.equal(service, "publish");
      state.publications.push(payload);
    },
  };
  return { hass, state };
}
function response(id) {
  return {
    schema_version: 1,
    kind: "daily_history",
    request_id: id,
    page_index: 0,
    page_count: 1,
    start_date: "2026-11-03",
    end_date_exclusive: "2026-11-05",
    days: ["2026-11-03", "2026-11-04"].map(date => ({
      date, console_seconds: 100, gaming_seconds: 50,
      non_gaming_seconds: 50, console_sessions: 1,
      gaming_sessions: 1, games: [{
        title_name: "Minecraft", duration_seconds: 50,
        session_count: 1,
      }],
    })),
  };
}

test("validates exact consecutive days", () => {
  assert.equal(validateDailyHistory(response("a"), "2026-11-03", "2026-11-05").days.length, 2);
  const invalid = response("a");
  invalid.days[1].date = "2026-11-03";
  assert.throws(() => validateDailyHistory(invalid, "2026-11-03", "2026-11-05"));
});
test("rejects invalid date and oversized ranges", async () => {
  const { hass } = fixture();
  const client = new PS5DailyHistoryClient(hass, { subscriptionDelayMs: 0 });
  await assert.rejects(client.getDays("2026-02-30", "2026-03-01"));
  await assert.rejects(client.getDays("2026-01-01", "2026-03-01"));
  client.dispose();
});
test("publishes and correlates daily responses", async () => {
  const { hass, state } = fixture();
  const client = new PS5DailyHistoryClient(hass, { subscriptionDelayMs: 0 });
  const pending = client.getDays("2026-11-03", "2026-11-05");
  await new Promise(resolve => setTimeout(resolve, 15));
  assert.equal(state.subscriptions[0].options.topic, "ps5-monitor/history/daily/response");
  assert.equal(state.publications[0].topic, "ps5-monitor/history/daily/request");
  assert.equal(state.publications[0].retain, false);
  const id = JSON.parse(state.publications[0].payload).request_id;
  state.subscriptions[0].callback({topic:"ps5-monitor/history/daily/response",payload:JSON.stringify(response("unrelated"))});
  assert.equal(client.pending.size, 1);
  state.subscriptions[0].callback({topic:"ps5-monitor/history/daily/response",payload:JSON.stringify(response(id))});
  assert.equal((await pending).days.length, 2);
  client.dispose();
  assert.equal(state.unsubscriptions, 1);
});
test("aborts pending requests and cleans up", async () => {
  const { hass } = fixture();
  const client = new PS5DailyHistoryClient(hass, { subscriptionDelayMs: 0 });
  const controller = new AbortController();
  const pending = client.getDays("2026-11-03", "2026-11-05", {signal: controller.signal});
  await new Promise(resolve => setTimeout(resolve, 15));
  controller.abort();
  await assert.rejects(pending, {name:"AbortError"});
  assert.equal(client.pending.size, 0);
  client.dispose();
});
test("connection replacement rejects old pending requests", async () => {
  const first = fixture(), second = fixture();
  const client = new PS5DailyHistoryClient(first.hass, { subscriptionDelayMs: 0 });
  const pending = client.getDays("2026-11-03", "2026-11-05");
  await new Promise(resolve => setTimeout(resolve, 15));
  client.updateHass(second.hass);
  await assert.rejects(pending, /connection changed/);
  assert.equal(first.state.unsubscriptions, 1);
  client.dispose();
});
test("rejects inconsistent gaming duration", () => {
  const data = response("a");
  data.days[0].gaming_seconds = 101;
  assert.throws(() => validateDailyHistory(data, "2026-11-03", "2026-11-05"));
});

test("assembles out-of-order daily pages and ignores duplicates", async () => {
  const { hass, state } = fixture();
  const client = new PS5DailyHistoryClient(hass, { subscriptionDelayMs: 0 });
  const pending = client.getDays("2026-11-03", "2026-11-05");
  await new Promise(resolve => setTimeout(resolve, 15));
  const id = JSON.parse(state.publications[0].payload).request_id;
  const full = response(id);
  const first = {...full, page_index: 0, page_count: 2, days: [full.days[0]]};
  const second = {...full, page_index: 1, page_count: 2, days: [full.days[1]]};
  const callback = state.subscriptions[0].callback;
  callback({topic:"ps5-monitor/history/daily/response",payload:JSON.stringify(second)});
  callback({topic:"ps5-monitor/history/daily/response",payload:JSON.stringify(second)});
  assert.equal(client.pending.size, 1);
  callback({topic:"ps5-monitor/history/daily/response",payload:JSON.stringify(first)});
  assert.equal((await pending).days.length, 2);
  client.dispose();
});

test("rejects a correlated server_busy error", async () => {
  const { hass, state } = fixture();
  const client = new PS5DailyHistoryClient(hass, { subscriptionDelayMs: 0 });
  const pending = client.getDays("2026-11-03", "2026-11-05");
  await new Promise(resolve => setTimeout(resolve, 15));
  const id = JSON.parse(state.publications[0].payload).request_id;
  state.subscriptions[0].callback({
    topic:"ps5-monitor/history/daily/response",
    payload:JSON.stringify({kind:"daily_history_error",request_id:id,error_code:"server_busy"}),
  });
  await assert.rejects(pending,/server_busy/);
  client.dispose();
});
