/**
 * PS5 Dashboard - Historical MQTT Client.
 *
 * Version: 1.1.0
 *
 * Provides historical statistics through the existing
 * authenticated Home Assistant WebSocket connection.
 *
 * Features:
 * - Shared MQTT response subscription.
 * - Unique request correlation.
 * - Concurrent request management.
 * - Request cancellation using AbortSignal.
 * - Configurable request timeout.
 * - Strict historical response validation.
 * - Safe subscription and resource cleanup.
 *
 * The client does not store authentication credentials.
 */

const REQUEST_TOPIC = "ps5-monitor/history/request";
const RESPONSE_TOPIC = "ps5-monitor/history/response";

const DEFAULT_TIMEOUT_MS = 30000;
const SUBSCRIPTION_DELAY_MS = 2000;

const PERIOD_PATTERN = /^\d{4}-(0[1-9]|1[0-2])$/;
const REQUEST_ID_PATTERN = /^[A-Za-z0-9_-]{1,64}$/;

export class PS5HistoryClient {
  /**
   * Initialize the historical MQTT client.
   *
   * @param {object} hass Home Assistant frontend instance.
   * @param {object} options Optional client configuration.
   */
  constructor(hass, options = {}) {
    if (!hass?.connection?.subscribeMessage) {
      throw new Error(
        "Home Assistant WebSocket connection is unavailable.",
      );
    }

    if (typeof hass.callService !== "function") {
      throw new Error(
        "Home Assistant service interface is unavailable.",
      );
    }

    this.hass = hass;

    this.timeoutMs =
      options.timeoutMs ?? DEFAULT_TIMEOUT_MS;

    if (
      !Number.isFinite(this.timeoutMs) ||
      this.timeoutMs <= 0
    ) {
      throw new RangeError(
        "Request timeout must be a positive number.",
      );
    }

    this.pendingRequests = new Map();

    this.unsubscribe = null;
    this.subscriptionPromise = null;

    this.disposed = false;
    this.generation = 0;
  }

  /**
   * Update the Home Assistant instance without rebuilding
   * the client or discarding active subscriptions.
   *
   * @param {object} hass Updated Home Assistant instance.
   */
  updateHass(hass) {
    if (this.disposed) {
      throw new Error("Historical client is disposed.");
    }

    if (!hass?.connection || !hass?.callService) {
      throw new Error("Invalid Home Assistant instance.");
    }

    if (hass.connection !== this.hass.connection) {
      this._resetConnection();
    }

    this.hass = hass;
  }

  /**
   * Create a backend-compatible request identifier.
   *
   * @returns {string}
   */
  createRequestId() {
    // Use cryptographically secure random bytes when available.
    // crypto.randomUUID() is unavailable in some HTTP contexts.
    if (!globalThis.crypto?.getRandomValues) {
      throw new Error(
        "Secure random number generation is unavailable.",
      );
    }

    const bytes = new Uint8Array(16);
    globalThis.crypto.getRandomValues(bytes);

    const identifier = Array.from(
      bytes,
      (byte) => byte.toString(16).padStart(2, "0"),
    ).join("");

    const requestId = `ps5-${identifier}`;

    if (!REQUEST_ID_PATTERN.test(requestId)) {
      throw new Error("Generated request ID is invalid.");
    }

    return requestId;
  }

  /**
   * Validate a canonical calendar month.
   *
   * @param {string} period YYYY-MM.
   */
  validatePeriod(period) {
    if (
      typeof period !== "string" ||
      !PERIOD_PATTERN.test(period)
    ) {
      throw new Error("Invalid calendar period.");
    }

    const [year, month] = period.split("-").map(Number);

    const now = new Date();

    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth() + 1;

    if (
      year < 2020 ||
      year > currentYear ||
      (year === currentYear && month > currentMonth)
    ) {
      throw new Error("Calendar period is outside supported range.");
    }
  }

  /**
   * Validate a historical response from the backend.
   *
   * @param {object} data Parsed MQTT response.
   * @param {string} expectedPeriod Requested calendar month.
   * @returns {object}
   */
  validateResponse(data, expectedPeriod) {
    if (!data || typeof data !== "object") {
      throw new Error("Invalid historical response.");
    }

    if (data.schema_version !== 1) {
      throw new Error("Unsupported historical schema version.");
    }

    if (data.period !== expectedPeriod) {
      throw new Error("Historical response period mismatch.");
    }

    if (
      !data.summary ||
      typeof data.summary !== "object"
    ) {
      throw new Error("Historical summary is missing.");
    }

    for (const field of [
      "console_seconds",
      "gaming_seconds",
      "gaming_sessions",
    ]) {
      const value = data.summary[field];

      if (
        typeof value !== "number" ||
        !Number.isFinite(value) ||
        value < 0
      ) {
        throw new Error(
          `Invalid historical summary field: ${field}`,
        );
      }
    }

    if (!Array.isArray(data.games)) {
      throw new Error("Historical games must be an array.");
    }

    if (
      !Number.isInteger(data.game_count) ||
      data.game_count !== data.games.length
    ) {
      throw new Error("Historical game count mismatch.");
    }

    for (const game of data.games) {
      if (
        !game ||
        typeof game.title_name !== "string" ||
        typeof game.duration_seconds !== "number" ||
        !Number.isFinite(game.duration_seconds) ||
        game.duration_seconds < 0 ||
        !Number.isInteger(game.session_count) ||
        game.session_count < 0 ||
        !(
          game.title_image === null ||
          typeof game.title_image === "string"
        )
      ) {
        throw new Error("Invalid historical game metadata.");
      }
    }

    return data;
  }

  /**
   * Process one MQTT response received through WebSocket.
   *
   * @param {object} message MQTT event.
   */
  _handleMessage(message) {
    if (this.disposed) {
      return;
    }

    if (message?.topic !== RESPONSE_TOPIC) {
      return;
    }

    let data;

    try {
      data =
        typeof message.payload === "string"
          ? JSON.parse(message.payload)
          : message.payload;
    } catch {
      // Invalid messages from unrelated publishers must not
      // interrupt valid requests.
      return;
    }

    const requestId = data?.request_id;

    if (typeof requestId !== "string") {
      return;
    }

    const pending = this.pendingRequests.get(requestId);

    if (!pending) {
      return;
    }

    try {
      const response = this.validateResponse(
        data,
        pending.period,
      );

      pending.resolve(response);
    } catch (error) {
      pending.reject(error);
    }
  }

  /**
   * Establish the shared historical response subscription.
   *
   * @returns {Promise<void>}
   */
  async connect() {
    if (this.disposed) {
      throw new Error("Historical client is disposed.");
    }

    if (this.subscriptionPromise) {
      return this.subscriptionPromise;
    }

    const generation = this.generation;
    const connection = this.hass.connection;

    const subscriptionPromise = (async () => {
      const unsubscribe = await connection.subscribeMessage(
        (message) => {
          if (generation === this.generation) {
            this._handleMessage(message);
          }
        },
        {
          type: "mqtt/subscribe",
          topic: RESPONSE_TOPIC,
          qos: 1,
        },
      );

      if (
        this.disposed ||
        generation !== this.generation
      ) {
        unsubscribe();
        throw new Error("Historical connection was replaced.");
      }

      this.unsubscribe = unsubscribe;

      // Allow the broker subscription to propagate.
      // This is a compatibility delay, not a formal MQTT SUBACK.
      await new Promise((resolve) => {
        setTimeout(resolve, SUBSCRIPTION_DELAY_MS);
      });

      if (
        this.disposed ||
        generation !== this.generation
      ) {
        throw new Error("Historical connection was replaced.");
      }
    })();

    this.subscriptionPromise = subscriptionPromise;

    try {
      await subscriptionPromise;
    } catch (error) {
      if (this.subscriptionPromise === subscriptionPromise) {
        this.subscriptionPromise = null;
      }

      throw error;
    }
  }

  /**
   * Request one historical calendar month.
   *
   * @param {string} period YYYY-MM.
   * @param {object} options Request options.
   * @returns {Promise<object>}
   */
  async getMonth(period, options = {}) {
    this.validatePeriod(period);

    if (this.disposed) {
      throw new Error("Historical client is disposed.");
    }

    const signal = options.signal;

    if (signal?.aborted) {
      throw new DOMException(
        "Historical request cancelled.",
        "AbortError",
      );
    }

    await this.connect();

    if (signal?.aborted) {
      throw new DOMException(
        "Historical request cancelled.",
        "AbortError",
      );
    }

    const requestId = this.createRequestId();

    let timeoutId = null;
    let abortHandler = null;

    let resolveRequest;
    let rejectRequest;

    const responsePromise = new Promise((resolve, reject) => {
      resolveRequest = resolve;
      rejectRequest = reject;
    });

    // Register a rejection handler immediately, including when
    // MQTT publication fails before awaiting the response.
    responsePromise.catch(() => {});

    const cleanup = () => {
      if (timeoutId !== null) {
        clearTimeout(timeoutId);
        timeoutId = null;
      }

      if (signal && abortHandler) {
        signal.removeEventListener("abort", abortHandler);
      }

      this.pendingRequests.delete(requestId);
    };

    const settle = (callback, value) => {
      if (!this.pendingRequests.has(requestId)) {
        return;
      }

      cleanup();
      callback(value);
    };

    this.pendingRequests.set(requestId, {
      period,
      resolve: (value) => settle(resolveRequest, value),
      reject: (error) => settle(rejectRequest, error),
    });

    timeoutId = setTimeout(() => {
      this.pendingRequests.get(requestId)?.reject(
        new Error("Historical request timed out."),
      );
    }, this.timeoutMs);

    if (signal) {
      abortHandler = () => {
        this.pendingRequests.get(requestId)?.reject(
          new DOMException(
            "Historical request cancelled.",
            "AbortError",
          ),
        );
      };

      signal.addEventListener("abort", abortHandler, {
        once: true,
      });

      if (signal.aborted) {
        abortHandler();
      }
    }

    try {
      if (signal?.aborted) {
        return await responsePromise;
      }

      await this.hass.callService("mqtt", "publish", {
        topic: REQUEST_TOPIC,
        payload: JSON.stringify({
          request_id: requestId,
          period,
        }),
        qos: 1,
        retain: false,
      });

      return await responsePromise;
    } catch (error) {
      this.pendingRequests.get(requestId)?.reject(error);
      throw error;
    } finally {
      cleanup();
    }
  }

  /**
   * Cancel pending requests and release a replaced connection.
   */
  _resetConnection() {
    this.generation += 1;

    for (const pending of this.pendingRequests.values()) {
      pending.reject(
        new Error("Home Assistant connection changed."),
      );
    }

    if (typeof this.unsubscribe === "function") {
      this.unsubscribe();
    }

    this.unsubscribe = null;
    this.subscriptionPromise = null;
  }

  /**
   * Release all resources when the dashboard card is removed.
   */
  dispose() {
    if (this.disposed) {
      return;
    }

    this._resetConnection();
    this.disposed = true;
  }
}
