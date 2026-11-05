/**
 * PS5 Dashboard - Formatter Tests.
 *
 * Validate duration conversion and calendar boundaries.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(
  new URL("../services/ps5-formatters.js", import.meta.url),
  "utf8",
);

const moduleUrl = `data:text/javascript;base64,${
  Buffer.from(source).toString("base64")
}`;

const {
  formatDuration,
  formatSensorHours,
  formatPeriod,
  shiftPeriod,
  getCurrentPeriod,
} = await import(moduleUrl);

test("formats confirmed durations", () => {
  assert.equal(formatDuration(0), "0h 00m");
  assert.equal(formatDuration(3600), "1h 00m");
  assert.equal(formatDuration(5400), "1h 30m");
  assert.equal(formatDuration(3737.8), "1h 02m");
  assert.equal(formatDuration(-1), "—");
});

test("formats Home Assistant decimal hours", () => {
  assert.equal(formatSensorHours("1.463"), "1h 28m");
  assert.equal(formatSensorHours("0"), "0h 00m");
  assert.equal(formatSensorHours("unknown"), "—");
  assert.equal(formatSensorHours("unavailable"), "—");
});

test("formats calendar periods", () => {
  assert.equal(formatPeriod("2026-11"), "November 2026");
  assert.equal(formatPeriod("2026-01"), "January 2026");
  assert.equal(formatPeriod("2026-13"), "Invalid period");
});

test("navigates across calendar years", () => {
  assert.equal(shiftPeriod("2026-01", -1), "2025-12");
  assert.equal(shiftPeriod("2025-12", 1), "2026-01");
  assert.equal(shiftPeriod("2026-11", -12), "2025-11");
});

test("returns a canonical current period", () => {
  assert.match(getCurrentPeriod(), /^\d{4}-\d{2}$/);
});
