/**
 * PS5 Dashboard - Intelligent History Navigation Tests.
 *
 * Validate navigation across sparse gaming history,
 * calendar boundaries, empty indexes, and invalid data.
 *
 * All tests are isolated and require no Home Assistant
 * connection or MQTT broker.
 */

import assert from "node:assert/strict";
import test from "node:test";

import {
  getGamingPeriods,
  findAdjacentGamingPeriod,
  getHistoryNavigation,
} from "../services/ps5-history-navigation.js";

/**
 * Create a complete 36-month historical index.
 *
 * The index starts in December 2023 and ends in
 * November 2026.
 *
 * @param {string[]} gamingMonths
 * @returns {object}
 */
function createIndex(gamingMonths = []) {
  const months = [];

  for (let offset = 0; offset < 36; offset++) {
    const absoluteMonth = 2023 * 12 + 11 + offset;

    const year = Math.floor(absoluteMonth / 12);
    const month = absoluteMonth % 12 + 1;

    const period = `${year}-${String(month).padStart(2, "0")}`;

    months.push({
      month: period,
      has_gaming: gamingMonths.includes(period),
    });
  }

  return {
    schema_version: 1,
    month_count: 36,
    months,
  };
}

test("extracts sparse gaming months", () => {
  const index = createIndex([
    "2024-01",
    "2025-06",
    "2026-11",
  ]);

  assert.deepEqual(
    getGamingPeriods(index),
    ["2024-01", "2025-06", "2026-11"],
  );
});

test("skips consecutive empty months", () => {
  const periods = getGamingPeriods(
    createIndex(["2024-01", "2026-11"]),
  );

  assert.equal(
    findAdjacentGamingPeriod(periods, "2026-11", -1),
    "2024-01",
  );
});

test("finds the next gaming month", () => {
  const periods = getGamingPeriods(
    createIndex(["2024-01", "2025-06"]),
  );

  assert.equal(
    findAdjacentGamingPeriod(periods, "2024-01", 1),
    "2025-06",
  );
});

test("disables navigation beyond available activity", () => {
  const periods = getGamingPeriods(
    createIndex(["2024-01", "2026-11"]),
  );

  assert.equal(
    getHistoryNavigation(periods, "2024-01").previous,
    null,
  );

  assert.equal(
    getHistoryNavigation(periods, "2026-11").next,
    null,
  );
});

test("supports navigation from an empty current month", () => {
  const periods = getGamingPeriods(
    createIndex(["2024-01", "2026-10"]),
  );

  assert.deepEqual(
    getHistoryNavigation(periods, "2026-11"),
    {
      previous: "2026-10",
      next: null,
    },
  );
});

test("handles a completely empty gaming history", () => {
  const periods = getGamingPeriods(createIndex());

  assert.deepEqual(periods, []);

  assert.deepEqual(
    getHistoryNavigation(periods, "2026-11"),
    {
      previous: null,
      next: null,
    },
  );
});

test("handles December to January transitions", () => {
  const periods = getGamingPeriods(
    createIndex(["2025-12", "2026-01"]),
  );

  assert.equal(
    findAdjacentGamingPeriod(periods, "2025-12", 1),
    "2026-01",
  );

  assert.equal(
    findAdjacentGamingPeriod(periods, "2026-01", -1),
    "2025-12",
  );
});

test("rejects an incomplete historical index", () => {
  const index = createIndex();

  index.months.pop();

  assert.throws(
    () => getGamingPeriods(index),
    /Invalid historical activity index/,
  );
});

test("rejects nonconsecutive calendar months", () => {
  const index = createIndex();

  index.months[10].month = "2024-11";

  assert.throws(
    () => getGamingPeriods(index),
    /Historical months must be consecutive/,
  );
});

test("rejects invalid navigation directions", () => {
  assert.throws(
    () => findAdjacentGamingPeriod([], "2026-11", 0),
    /Invalid navigation arguments/,
  );
});
