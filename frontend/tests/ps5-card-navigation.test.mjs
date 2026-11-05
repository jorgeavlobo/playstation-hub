/**
 * PS5 Dashboard - Card Navigation Integration Tests.
 *
 * Verify navigation behavior independently of Home Assistant,
 * MQTT, and the browser DOM.
 *
 * The tests use the actual dashboard card implementation.
 */

import assert from "node:assert/strict";
import test from "node:test";

import {
  getCurrentPeriod,
  shiftPeriod,
} from "../services/ps5-formatters.js";

/**
 * Build a valid 36-month historical index.
 *
 * @param {string[]} activeMonths
 * @returns {object}
 */
function createIndex(activeMonths = []) {
  const current = getCurrentPeriod();
  const months = [];

  for (let offset = -35; offset <= 0; offset++) {
    const period = shiftPeriod(current, offset);

    months.push({
      month: period,
      has_gaming: activeMonths.includes(period),
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
 * Create a minimal browser-compatible custom element.
 */
class MockHTMLElement {
  constructor() {
    this.isConnected = true;
    this.shadowRoot = null;
  }

  attachShadow() {
    this.shadowRoot = {
      append() {},
      replaceChildren() {},
    };

    return this.shadowRoot;
  }
}

globalThis.HTMLElement = MockHTMLElement;

const registry = new Map();

globalThis.customElements = {
  get(name) {
    return registry.get(name);
  },

  define(name, constructor) {
    registry.set(name, constructor);
  },
};

globalThis.window = {
  customCards: [],
};

const { validateHistoryIndex } = await import(
  "../services/ps5-history-index-client.js"
);

await import("../ps5-dashboard-card.js");

const Card = registry.get("ps5-dashboard-card");

assert.ok(Card, "Dashboard card was not registered.");

/**
 * Construct a card without Home Assistant dependencies.
 */
function createCard(activeMonths) {
  const card = new Card();

  const index = createIndex(activeMonths);

  card._historyIndex = validateHistoryIndex(index).index;

  card._gamingPeriods = activeMonths;

  card._loadMonth = async () => {};

  return card;
}

test("navigates to the previous gaming month", () => {
  const current = getCurrentPeriod();
  const previous = shiftPeriod(current, -10);

  const card = createCard([previous, current]);

  card._period = current;
  card._changeMonth(-1);

  assert.equal(card._period, previous);
});

test("skips months without gaming activity", () => {
  const current = getCurrentPeriod();

  const older = shiftPeriod(current, -30);
  const newer = shiftPeriod(current, -5);

  const card = createCard([older, newer]);

  card._period = current;
  card._changeMonth(-1);

  assert.equal(card._period, newer);

  card._changeMonth(-1);

  assert.equal(card._period, older);
});

test("navigates forward to the next gaming month", () => {
  const current = getCurrentPeriod();

  const older = shiftPeriod(current, -20);
  const newer = shiftPeriod(current, -5);

  const card = createCard([older, newer]);

  card._period = older;
  card._changeMonth(1);

  assert.equal(card._period, newer);
});

test("allows returning to the current month", () => {
  const current = getCurrentPeriod();
  const previous = shiftPeriod(current, -5);

  const card = createCard([previous]);

  card._period = previous;
  card._changeMonth(1);

  assert.equal(card._period, current);
});

test("does not navigate beyond the oldest gaming month", () => {
  const current = getCurrentPeriod();
  const oldest = shiftPeriod(current, -25);

  const card = createCard([oldest]);

  card._period = oldest;
  card._changeMonth(-1);

  assert.equal(card._period, oldest);
});

test("disables navigation when no gaming history exists", () => {
  const current = getCurrentPeriod();

  const card = createCard([]);

  card._period = current;

  const targets = card._getNavigationTargets();

  assert.equal(targets.previous, null);
  assert.equal(targets.next, null);
});

test("rejects future navigation", () => {
  const current = getCurrentPeriod();

  const card = createCard([current]);

  card._period = current;
  card._changeMonth(1);

  assert.equal(card._period, current);
});

test("updates navigation controls without rebuilding the dashboard", () => {
  /**
   * Verify that navigation updates modify only the existing
   * controls and preserve their object identities.
   */

  const current = getCurrentPeriod();
  const previous = shiftPeriod(current, -6);

  const card = createCard([previous]);

  card._period = current;

  const previousButton = { disabled: true };
  const nextButton = { disabled: true };
  const label = { textContent: "" };

  card._navigationElements = {
    previous: previousButton,
    next: nextButton,
    label,
  };

  const originalElements = card._navigationElements;

  card._updateNavigation();

  assert.equal(previousButton.disabled, false);
  assert.equal(nextButton.disabled, true);
  assert.equal(label.textContent.length > 0, true);

  assert.strictEqual(
    card._navigationElements,
    originalElements,
  );

  card._period = previous;
  card._updateNavigation();

  assert.equal(previousButton.disabled, true);
  assert.equal(nextButton.disabled, false);

  assert.strictEqual(
    card._navigationElements.previous,
    previousButton,
  );

  assert.strictEqual(
    card._navigationElements.next,
    nextButton,
  );
});

test("receiving an index updates navigation controls immediately", () => {
  /**
   * Verify that a valid MQTT index update refreshes the
   * existing navigation controls without calling _render().
   */

  const current = getCurrentPeriod();
  const previous = shiftPeriod(current, -4);

  const card = createCard([]);

  card._period = current;

  const previousButton = { disabled: true };
  const nextButton = { disabled: true };
  const label = { textContent: "" };

  card._navigationElements = {
    previous: previousButton,
    next: nextButton,
    label,
  };

  let renderCalls = 0;

  card._render = () => {
    renderCalls += 1;
  };

  const index = createIndex([previous]);

  // Clear the previously cached index to simulate the
  // first valid MQTT publication.
  card._historyIndex = null;

  card._onHistoryIndex(
    validateHistoryIndex(index),
  );

  assert.equal(previousButton.disabled, false);
  assert.equal(nextButton.disabled, true);
  assert.equal(renderCalls, 0);
});

test("restores MQTT clients after card reinsertion", () => {
  /**
   * Verify that card reinsertion restores both MQTT clients
   * using the previously assigned Home Assistant instance.
   *
   * The test does not establish network connections.
   */

  const card = new Card();

  const hass = {
    connection: {
      subscribeMessage: async () => () => {},
    },
    callService: async () => {},
    states: {},
  };

  // Avoid actual monthly requests and DOM rendering.
  card._render = () => {};
  card._loadMonth = async () => {};

  card.hass = hass;

  const originalHistoryClient = card._client;
  const originalIndexClient = card._indexClient;

  assert.ok(originalHistoryClient);
  assert.ok(originalIndexClient);

  // Simulate removal from the dashboard.
  card.disconnectedCallback();

  assert.equal(card._client, null);
  assert.equal(card._indexClient, null);

  assert.equal(originalHistoryClient.disposed, true);
  assert.equal(originalIndexClient.disposed, true);

  // Simulate reinsertion without another hass setter call.
  card.connectedCallback();

  assert.ok(card._client);
  assert.ok(card._indexClient);

  assert.notStrictEqual(
    card._client,
    originalHistoryClient,
  );

  assert.notStrictEqual(
    card._indexClient,
    originalIndexClient,
  );

  assert.equal(card._client.disposed, false);
  assert.equal(card._indexClient.disposed, false);

  // Clean up any asynchronous subscription activity.
  card.disconnectedCallback();
});

test("invalidates the historical index after calendar rollover", () => {
  /**
   * Simulate a calendar transition without changing the
   * operating system clock.
   */

  const current = getCurrentPeriod();
  const previous = shiftPeriod(current, -1);

  const card = createCard([previous]);

  card._calendarPeriod = previous;
  card._period = current;

  card._checkCalendarRollover();

  assert.equal(card._calendarPeriod, current);
  assert.equal(card._historyIndex, null);
  assert.deepEqual(card._gamingPeriods, []);
  assert.equal(card._indexLoading, true);
});

test("follows the current month after calendar rollover", () => {
  /**
   * A card displaying the previous current month must
   * automatically select the new current month.
   */

  const current = getCurrentPeriod();
  const previous = shiftPeriod(current, -1);

  const card = createCard([previous]);

  card._calendarPeriod = previous;
  card._period = previous;
  card._history = { summary: {} };

  card._checkCalendarRollover();

  assert.equal(card._period, current);
  assert.equal(card._history, null);
  assert.equal(card._error, null);
});

test("preserves historical selection after calendar rollover", () => {
  /**
   * A user viewing an older historical month must not
   * lose the selected period when the calendar changes.
   */

  const current = getCurrentPeriod();
  const previous = shiftPeriod(current, -1);
  const historical = shiftPeriod(current, -8);

  const card = createCard([historical]);

  card._calendarPeriod = previous;
  card._period = historical;

  card._checkCalendarRollover();

  assert.equal(card._calendarPeriod, current);
  assert.equal(card._period, historical);
  assert.equal(card._historyIndex, null);
});

test("calendar rollover schedules exactly one monthly reload", () => {
  /**
   * Verify that a calendar rollover requests the new month
   * exactly once through the existing Home Assistant setter.
   *
   * No real MQTT connection or browser rendering is used.
   */

  const current = getCurrentPeriod();
  const previous = shiftPeriod(current, -1);

  const card = createCard([]);

  card._calendarPeriod = previous;
  card._period = previous;
  card._history = { summary: {} };

  let reloadCount = 0;

  card._loadMonth = async () => {
    reloadCount += 1;

    // Match the synchronous loading-state transition
    // performed by the production _loadMonth method.
    card._loading = true;
  };

  card._render = () => {};

  const hass = {
    connection: {
      subscribeMessage: async () => () => {},
    },
    callService: async () => {},
    states: {},
  };

  card.hass = hass;

  assert.equal(card._period, current);
  assert.equal(reloadCount, 1);
  assert.equal(card._rolloverReloadPending, false);

  card.hass = hass;

  assert.equal(reloadCount, 1);

  card.disconnectedCallback();
});

test("outdated monthly response cannot replace new month", async () => {
  /**
   * Verify that an older monthly response cannot overwrite
   * a newer response using the production _loadMonth method.
   *
   * The shared fixture replaces _loadMonth with a stub.
   * Restore the original method for this concurrency test.
   */

  const current = getCurrentPeriod();
  const previous = shiftPeriod(current, -1);

  const card = createCard([]);

  // Restore the actual production method inherited from
  // the dashboard custom element prototype.
  card._loadMonth = Card.prototype._loadMonth.bind(card);

  const pending = new Map();

  card._client = {
    getMonth(period) {
      return new Promise((resolve) => {
        pending.set(period, resolve);
      });
    },
  };

  card._render = () => {};

  card._period = previous;

  const oldRequest = card._loadMonth();

  // Wait for the request to reach the simulated client.
  await Promise.resolve();

  assert.ok(pending.has(previous));

  card._period = current;

  const newRequest = card._loadMonth();

  await Promise.resolve();

  assert.ok(pending.has(current));

  const currentResponse = {
    period: current,
    summary: {
      gaming_seconds: 3600,
      gaming_sessions: 1,
    },
    games: [],
  };

  pending.get(current)(currentResponse);

  await newRequest;

  assert.strictEqual(card._history, currentResponse);

  const previousResponse = {
    period: previous,
    summary: {
      gaming_seconds: 7200,
      gaming_sessions: 2,
    },
    games: [],
  };

  pending.get(previous)(previousResponse);

  await oldRequest;

  assert.strictEqual(card._history, currentResponse);
  assert.equal(card._period, current);
});

test("updates historical navigation status incrementally", () => {
  /**
   * Verify loading, unavailable, and ready states.
   *
   * The test uses the production navigation updater
   * without creating a real browser DOM.
   */

  const card = createCard([]);

  const previous = { disabled: false };
  const next = { disabled: false };
  const label = { textContent: "" };
  const status = {
    textContent: "",
    hidden: false,
  };

  card._navigationElements = {
    previous,
    next,
    label,
    status,
  };

  const originalElements = card._navigationElements;

  // No index has been received yet.
  card._historyIndex = null;
  card._indexLoading = true;
  card._indexError = null;

  card._updateNavigation();

  assert.equal(
    status.textContent,
    "Loading history navigation…",
  );

  assert.equal(status.hidden, false);
  assert.equal(previous.disabled, true);
  assert.equal(next.disabled, true);

  // Simulate a subscription failure.
  card._indexLoading = false;
  card._indexError = "Simulated subscription failure.";

  card._updateNavigation();

  assert.equal(
    status.textContent,
    "History navigation unavailable",
  );

  assert.equal(status.hidden, false);

  // Simulate successful recovery with a valid index.
  const current = getCurrentPeriod();
  const active = shiftPeriod(current, -3);

  const validated = validateHistoryIndex(
    createIndex([active]),
  );

  card._historyIndex = validated.index;
  card._gamingPeriods = validated.gamingPeriods;
  card._indexLoading = false;
  card._indexError = null;

  card._updateNavigation();

  assert.equal(status.textContent, "");
  assert.equal(status.hidden, true);
  assert.equal(previous.disabled, false);

  // The existing controls must remain unchanged.
  assert.strictEqual(
    card._navigationElements,
    originalElements,
  );

  assert.strictEqual(
    card._navigationElements.status,
    status,
  );
});

test("daily chart supports week and month windows", () => {
  const card = new Card();
  card._chartMode = "week";
  const week = card._getDailyWindow();
  const dayCount = (Date.parse(`${week.end}T00:00:00Z`) -
    Date.parse(`${week.start}T00:00:00Z`)) / 86400000;
  assert.equal(dayCount, 7);

  card._chartMode = "month";
  const month = card._getDailyWindow();
  const monthCount = (Date.parse(`${month.end}T00:00:00Z`) -
    Date.parse(`${month.start}T00:00:00Z`)) / 86400000;
  assert.ok(monthCount >= 1 && monthCount <= 31);
});

test("switching away from daily charts invalidates stale requests", () => {
  const card = new Card();
  const controller = new AbortController();
  card._dailyController = controller;
  card._dailyRequestGeneration = 2;
  card._dailyLoading = true;
  card._cancelDailyHistory();
  assert.equal(controller.signal.aborted, true);
  assert.equal(card._dailyRequestGeneration, 3);
  assert.equal(card._dailyLoading, false);
});

test("first row does not invent session timestamps or durations", () => {
  const card = new Card();
  const start = { textContent: "uninitialized" };
  const duration = { textContent: "uninitialized" };
  const power = { textContent: "", className: "" };
  const status = { textContent: "", className: "" };
  const title = { textContent: "" };
  const note = { textContent: "" };
  const cover = { hidden: true, src: "", alt: "" };
  const backdrop = { style: {} };
  card._heroElements = {
    start, duration, power, status, title, note, cover, backdrop,
  };
  card._liveState = {
    schema_version: 1, available: true, console_active: true,
    player_gaming: true, title_name: "EA SPORTS FC 26",
    title_image: null, observed_at: new Date().toISOString(),
  };
  card._updateLiveHero();
  assert.equal(start.textContent, "—");
  assert.equal(duration.textContent, "—");
  assert.equal(power.textContent, "Ligada");
  assert.equal(title.textContent, "EA SPORTS FC 26");
});

test("weekly total uses confirmed daily seconds", async () => {
  const card = new Card();
  card._metricElements = new Map();
  card._hass = { states: {} };
  card._dailyClient = {
    async getDays(start, end) {
      assert.match(start, /^\d{4}-\d{2}-\d{2}$/);
      assert.match(end, /^\d{4}-\d{2}-\d{2}$/);
      return { days: [
        { gaming_seconds: 120 },
        { gaming_seconds: 240 },
      ] };
    },
  };
  card._refreshWeeklyMetric();
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(card._weeklySeconds, 360);
  card._weeklyGeneration++;
  card._weeklyAbort?.abort();
});
