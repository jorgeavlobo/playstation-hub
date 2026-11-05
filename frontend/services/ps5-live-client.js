/**
 * Subscribe to the PS5 live-state feed using Home Assistant's existing
 * authenticated WebSocket. No credentials or MQTT connections are created.
 */
export const LIVE_TOPIC = "ps5-monitor/live/state";
const STALE_MS = 90000;

export function validateLiveState(value, now = Date.now()) {
  if (!value || value.schema_version !== 1 ||
      typeof value.available !== "boolean" ||
      typeof value.console_active !== "boolean" ||
      typeof value.player_gaming !== "boolean" ||
      typeof value.power !== "string" ||
      typeof value.activity !== "string" ||
      !Number.isSafeInteger(value.generation) || value.generation < 0 ||
      typeof value.observed_at !== "string") {
    throw new Error("Invalid PS5 live-state payload.");
  }
  const observed = Date.parse(value.observed_at);
  if (!Number.isFinite(observed) || observed > now + 30000) {
    throw new Error("Invalid PS5 observation timestamp.");
  }
  return {
    ...value,
    title_name: typeof value.title_name === "string" ? value.title_name : null,
    title_image: typeof value.title_image === "string" && /^https:\/\//.test(value.title_image) ? value.title_image : null,
    stale: now - observed > STALE_MS,
  };
}

export class PS5LiveClient {
  constructor(hass, onUpdate) {
    if (!hass?.connection?.subscribeMessage || typeof onUpdate !== "function") {
      throw new Error("Invalid PS5 live-state client arguments.");
    }
    this.hass = hass;
    this.onUpdate = onUpdate;
    this.unsubscribe = null;
    this.promise = null;
    this.generation = 0;
    this.disposed = false;
    this.last = null;
  }

  updateHass(hass) {
    if (this.disposed) throw new Error("Live client disposed.");
    if (!hass?.connection?.subscribeMessage) throw new Error("Invalid Home Assistant connection.");
    if (hass.connection !== this.hass.connection) this._reset();
    this.hass = hass;
  }

  async connect() {
    if (this.disposed) throw new Error("Live client disposed.");
    if (this.promise) return this.promise;
    const generation = this.generation;
    const connection = this.hass.connection;
    const promise = (async () => {
      const unsubscribe = await connection.subscribeMessage((message) => {
        if (this.disposed || generation !== this.generation || message?.topic !== LIVE_TOPIC) return;
        try {
          const payload = typeof message.payload === "string" ? JSON.parse(message.payload) : message.payload;
          const live = validateLiveState(payload);
          if (this.last && (live.generation < this.last.generation ||
              Date.parse(live.observed_at) < Date.parse(this.last.observed_at))) return;
          this.last = live;
          this.onUpdate(live);
        } catch (error) {
          console.warn("Rejected PS5 live-state publication:", error);
        }
      }, { type: "mqtt/subscribe", topic: LIVE_TOPIC, qos: 1 });
      if (this.disposed || generation !== this.generation) {
        unsubscribe();
        throw new Error("PS5 live-state connection replaced.");
      }
      this.unsubscribe = unsubscribe;
    })();
    this.promise = promise;
    try { await promise; }
    catch (error) {
      if (this.promise === promise) this.promise = null;
      throw error;
    }
  }

  _reset() {
    this.generation += 1;
    if (typeof this.unsubscribe === "function") this.unsubscribe();
    this.unsubscribe = null;
    this.promise = null;
    this.last = null;
  }

  dispose() {
    if (this.disposed) return;
    this._reset();
    this.disposed = true;
  }
}
