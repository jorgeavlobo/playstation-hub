/**
 * PS5 Dashboard - Daily History MQTT Client.
 *
 * Requests a bounded range of local calendar days over the existing
 * authenticated Home Assistant WebSocket and MQTT service.
 *
 * No credentials are stored. The client never writes to SQLite.
 */
const REQUEST_TOPIC = "ps5-monitor/history/daily/request";
const RESPONSE_TOPIC = "ps5-monitor/history/daily/response";
const DAY_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const MAX_DAYS = 31;
const MAX_RESPONSE_BYTES = 16384;

function parseDay(value) {
  if (typeof value !== "string" || !DAY_PATTERN.test(value)) {
    throw new TypeError("Expected YYYY-MM-DD date.");
  }
  const date = new Date(`${value}T00:00:00Z`);
  if (!Number.isFinite(date.getTime()) ||
      date.toISOString().slice(0, 10) !== value) {
    throw new RangeError("Invalid calendar date.");
  }
  return date;
}

export function validateDailyHistory(data, start, end) {
  if (!data || data.schema_version !== 1 ||
      data.kind !== "daily_history" ||
      data.start_date !== start ||
      data.end_date_exclusive !== end ||
      !Array.isArray(data.days)) {
    throw new Error("Invalid daily history response.");
  }
  const count = (parseDay(end) - parseDay(start)) / 86400000;
  if (data.days.length !== count) {
    throw new Error("Unexpected number of daily entries.");
  }
  for (let index = 0; index < count; index++) {
    const item = data.days[index];
    const expected = new Date(parseDay(start).getTime() + index * 86400000)
      .toISOString().slice(0, 10);
    if (!item || item.date !== expected ||
        !Array.isArray(item.games)) {
      throw new Error("Invalid daily history entry.");
    }
    for (const key of ["console_seconds", "gaming_seconds",
                       "non_gaming_seconds", "console_sessions",
                       "gaming_sessions"]) {
      if (!Number.isFinite(item[key]) || item[key] < 0) {
        throw new Error(`Invalid daily metric: ${key}`);
      }
    }
    if (item.gaming_seconds > item.console_seconds + 0.01) {
      throw new Error("Gaming duration exceeds console duration.");
    }
    for (const game of item.games) {
      if (!game || typeof game.title_name !== "string" ||
          !Number.isFinite(game.duration_seconds) ||
          game.duration_seconds < 0 ||
          !Number.isInteger(game.session_count) ||
          game.session_count < 0) {
        throw new Error("Invalid daily game entry.");
      }
    }
  }
  return data;
}

export class PS5DailyHistoryClient {
  constructor(hass, { timeoutMs = 30000, subscriptionDelayMs = 2000 } = {}) {
    if (typeof hass?.connection?.subscribeMessage !== "function" ||
        typeof hass?.callService !== "function") {
      throw new Error("Home Assistant MQTT interface unavailable.");
    }
    if (!Number.isFinite(timeoutMs) || timeoutMs <= 0 ||
        !Number.isFinite(subscriptionDelayMs) || subscriptionDelayMs < 0) {
      throw new RangeError("Invalid client timing configuration.");
    }
    this.hass = hass;
    this.timeoutMs = timeoutMs;
    this.subscriptionDelayMs = subscriptionDelayMs;
    this.pending = new Map();
    this.unsubscribe = null;
    this.subscriptionPromise = null;
    this.generation = 0;
    this.disposed = false;
  }

  updateHass(hass) {
    if (this.disposed) throw new Error("Daily history client disposed.");
    if (typeof hass?.connection?.subscribeMessage !== "function" ||
        typeof hass?.callService !== "function") {
      throw new Error("Invalid Home Assistant instance.");
    }
    if (hass.connection !== this.hass.connection) this._reset();
    this.hass = hass;
  }

  _onMessage(message) {
    if (this.disposed || message?.topic !== RESPONSE_TOPIC) return;
    let data;
    try {
      if (typeof message.payload === "string" &&
          new TextEncoder().encode(message.payload).length > MAX_RESPONSE_BYTES) {
        return;
      }
      data = typeof message.payload === "string"
        ? JSON.parse(message.payload) : message.payload;
    } catch { return; }
    const request = this.pending.get(data?.request_id);
    if (!request) return;
    try {
      if (data.kind === "daily_history_error") {
        const error = new Error(`Daily history unavailable: ${data.error_code}`);
        error.code = data.error_code;
        request.reject(error);
        return;
      }
      if (data.kind !== "daily_history" ||
          data.start_date !== request.start ||
          data.end_date_exclusive !== request.end ||
          data.schema_version !== 1) {
        throw new Error("Invalid daily history page metadata.");
      }
      const index = data.page_index;
      const count = data.page_count;
      if (!Number.isInteger(index) || !Number.isInteger(count) ||
          count < 1 || count > 31 || index < 0 || index >= count ||
          !Array.isArray(data.days)) {
        throw new Error("Invalid daily history pagination.");
      }
      if (request.pageCount !== null && request.pageCount !== count) {
        throw new Error("Inconsistent daily page count.");
      }
      request.pageCount = count;
      if (request.pages.has(index)) {
        if (JSON.stringify(request.pages.get(index)) !== JSON.stringify(data.days)) {
          throw new Error("Conflicting duplicate daily history page.");
        }
        return;
      }
      request.pages.set(index, data.days);
      if (request.pages.size !== count) return;
      const days = Array.from({ length: count }, (_, page) => {
        if (!request.pages.has(page)) throw new Error("Missing daily history page.");
        return request.pages.get(page);
      }).flat();
      request.resolve(validateDailyHistory({
        schema_version: 1, kind: "daily_history",
        request_id: data.request_id,
        start_date: request.start, end_date_exclusive: request.end, days,
      }, request.start, request.end));
    } catch (error) {
      request.reject(error);
    }
  }

  async connect() {
    if (this.disposed) throw new Error("Daily history client disposed.");
    if (this.subscriptionPromise) return this.subscriptionPromise;
    const generation = this.generation;
    const connection = this.hass.connection;
    const promise = (async () => {
      const unsubscribe = await connection.subscribeMessage(
        message => {
          if (generation === this.generation) this._onMessage(message);
        },
        { type: "mqtt/subscribe", topic: RESPONSE_TOPIC, qos: 1 },
      );
      if (this.disposed || generation !== this.generation) {
        unsubscribe();
        throw new Error("Daily history connection replaced.");
      }
      this.unsubscribe = unsubscribe;
      await new Promise(resolve => setTimeout(resolve, this.subscriptionDelayMs));
      if (this.disposed || generation !== this.generation) {
        throw new Error("Daily history connection replaced.");
      }
    })();
    this.subscriptionPromise = promise;
    try {
      await promise;
    } catch (error) {
      if (this.subscriptionPromise === promise) this.subscriptionPromise = null;
      throw error;
    }
  }

  async getDays(start, end, { signal } = {}) {
    const count = (parseDay(end) - parseDay(start)) / 86400000;
    if (!Number.isInteger(count) || count < 1 || count > MAX_DAYS) {
      throw new RangeError("Daily history range must be 1 to 31 days.");
    }
    if (this.disposed) throw new Error("Daily history client disposed.");
    if (signal?.aborted) throw new DOMException("Cancelled", "AbortError");
    await this.connect();
    if (signal?.aborted) throw new DOMException("Cancelled", "AbortError");

    const bytes = new Uint8Array(16);
    if (!globalThis.crypto?.getRandomValues) {
      throw new Error("Secure random generator unavailable.");
    }
    globalThis.crypto.getRandomValues(bytes);
    const requestId = `ps5-${Array.from(bytes, b =>
      b.toString(16).padStart(2, "0")).join("")}`;

    let timer;
    let abort;
    let resolvePromise;
    let rejectPromise;
    const result = new Promise((resolve, reject) => {
      resolvePromise = resolve;
      rejectPromise = reject;
    });
    result.catch(() => {});
    const cleanup = () => {
      clearTimeout(timer);
      signal?.removeEventListener("abort", abort);
      this.pending.delete(requestId);
    };
    const settle = (callback, value) => {
      if (!this.pending.has(requestId)) return;
      cleanup();
      callback(value);
    };
    this.pending.set(requestId, {
      start, end,
      pageCount: null,
      pages: new Map(),
      resolve: value => settle(resolvePromise, value),
      reject: error => settle(rejectPromise, error),
    });
    timer = setTimeout(() => this.pending.get(requestId)?.reject(
      new Error("Daily history request timed out.")), this.timeoutMs);
    abort = () => this.pending.get(requestId)?.reject(
      new DOMException("Cancelled", "AbortError"));
    signal?.addEventListener("abort", abort, { once: true });
    if (signal?.aborted) abort();

    try {
      if (!signal?.aborted) {
        await this.hass.callService("mqtt", "publish", {
          topic: REQUEST_TOPIC,
          payload: JSON.stringify({
            request_id: requestId,
            start_date: start,
            end_date_exclusive: end,
          }),
          qos: 1,
          retain: false,
        });
      }
    } catch (error) {
      this.pending.get(requestId)?.reject(error);
    }
    return result;
  }

  _reset() {
    this.generation++;
    for (const request of [...this.pending.values()]) {
      request.reject(new Error("Home Assistant connection changed."));
    }
    this.unsubscribe?.();
    this.unsubscribe = null;
    this.subscriptionPromise = null;
  }

  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    this._reset();
  }
}
