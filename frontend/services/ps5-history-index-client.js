/**
 * PS5 Dashboard - Historical Activity Index Client.
 *
 * Subscribe to the compact 36-month history index through
 * the existing authenticated Home Assistant WebSocket.
 *
 * Features:
 * - Independent MQTT subscription.
 * - Strict historical index validation.
 * - Current calendar-window verification.
 * - Safe reconnection and disposal.
 * - No additional MQTT broker connection.
 */

import {
  getGamingPeriods,
} from "./ps5-history-navigation.js?v=1.0.5";

const INDEX_TOPIC = "ps5-monitor/history/index";
const MONTH_COUNT = 36;

/**
 * Return the current local calendar period.
 *
 * @returns {string} YYYY-MM.
 */
function currentPeriod() {
  const now = new Date();

  return (
    `${now.getFullYear()}-` +
    `${String(now.getMonth() + 1).padStart(2, "0")}`
  );
}

/**
 * Convert a calendar period into an absolute month index.
 *
 * @param {string} period Calendar period.
 * @returns {number} Absolute month index.
 */
function monthIndex(period) {
  const [year, month] = period.split("-").map(Number);

  return year * 12 + month - 1;
}

/**
 * Validate a complete 36-month historical index.
 *
 * @param {object} index Parsed historical index.
 * @returns {object} Validated index.
 */
export function validateHistoryIndex(index) {
  const gamingPeriods = getGamingPeriods(index);

  const months = index.months;

  if (months.length !== MONTH_COUNT) {
    throw new Error("Invalid historical index length.");
  }

  const expectedCurrent = currentPeriod();

  if (months[months.length - 1].month !== expectedCurrent) {
    throw new Error(
      "Historical index does not match the current month."
    );
  }

  const first = monthIndex(months[0].month);
  const last = monthIndex(months[months.length - 1].month);

  if (last - first !== MONTH_COUNT - 1) {
    throw new Error("Invalid historical calendar window.");
  }

  if (
    typeof index.generated_at !== "string" ||
    !Number.isFinite(Date.parse(index.generated_at))
  ) {
    throw new Error("Invalid historical index timestamp.");
  }

  const generatedAt = Date.parse(index.generated_at);

  if (generatedAt > Date.now() + 60000) {
    throw new Error(
      "Historical index timestamp is in the future."
    );
  }

  return {
    index,
    gamingPeriods,
  };
}

/**
 * Manage the independent historical index subscription.
 */
export class PS5HistoryIndexClient {
  /**
   * @param {object} hass Home Assistant frontend instance.
   * @param {Function} onUpdate Validated index callback.
   */
  constructor(hass, onUpdate) {
    if (!hass?.connection?.subscribeMessage) {
      throw new Error(
        "Home Assistant WebSocket connection is unavailable."
      );
    }

    if (typeof onUpdate !== "function") {
      throw new TypeError(
        "History index callback must be a function."
      );
    }

    this.hass = hass;
    this.onUpdate = onUpdate;

    this.unsubscribe = null;
    this.subscriptionPromise = null;

    this.generation = 0;
    this.disposed = false;
    this.lastIndex = null;
  }

  /**
   * Process one MQTT history index publication.
   *
   * @param {object} message MQTT event.
   */
  _handleMessage(message) {
    if (
      this.disposed ||
      message?.topic !== INDEX_TOPIC
    ) {
      return;
    }

    try {
      const payload =
        typeof message.payload === "string"
          ? JSON.parse(message.payload)
          : message.payload;

      const validated = validateHistoryIndex(payload);

      this.lastIndex = validated.index;

      this.onUpdate(validated);
    } catch (error) {
      console.warn(
        "Rejected PS5 historical index:",
        error
      );
    }
  }

  /**
   * Establish one independent MQTT subscription.
   *
   * Concurrent connect calls reuse the same promise.
   */
  async connect() {
    if (this.disposed) {
      throw new Error("History index client is disposed.");
    }

    if (this.subscriptionPromise) {
      return this.subscriptionPromise;
    }

    const generation = this.generation;
    const connection = this.hass.connection;

    const promise = (async () => {
      const unsubscribe = await connection.subscribeMessage(
        (message) => {
          if (
            !this.disposed &&
            generation === this.generation
          ) {
            this._handleMessage(message);
          }
        },
        {
          type: "mqtt/subscribe",
          topic: INDEX_TOPIC,
          qos: 1,
        },
      );

      if (
        this.disposed ||
        generation !== this.generation
      ) {
        unsubscribe();

        throw new Error(
          "Historical index connection was replaced."
        );
      }

      this.unsubscribe = unsubscribe;
    })();

    this.subscriptionPromise = promise;

    try {
      await promise;
    } catch (error) {
      if (this.subscriptionPromise === promise) {
        this.subscriptionPromise = null;
      }

      throw error;
    }
  }

  /**
   * Update the Home Assistant instance.
   *
   * A changed WebSocket connection invalidates the
   * previous subscription and cached index.
   *
   * @param {object} hass Updated Home Assistant instance.
   */
  updateHass(hass) {
    if (this.disposed) {
      throw new Error("History index client is disposed.");
    }

    if (!hass?.connection?.subscribeMessage) {
      throw new Error("Invalid Home Assistant connection.");
    }

    if (hass.connection !== this.hass.connection) {
      this._resetConnection();
    }

    this.hass = hass;
  }

  /**
   * Release the current subscription and invalidate callbacks.
   */
  _resetConnection() {
    this.generation += 1;

    if (typeof this.unsubscribe === "function") {
      this.unsubscribe();
    }

    this.unsubscribe = null;
    this.subscriptionPromise = null;
    this.lastIndex = null;
  }

  /**
   * Release all resources permanently.
   */
  dispose() {
    if (this.disposed) {
      return;
    }

    this._resetConnection();
    this.disposed = true;
  }
}
