/**
 * PS5 Dashboard - Custom Lovelace Card.
 *
 * Version: 1.1.2
 *
 * Provides a responsive PlayStation-inspired dashboard using
 * Home Assistant entity states and historical MQTT statistics.
 *
 * This preview does not modify Lovelace configuration.
 */

import {
  PS5HistoryIndexClient,
  validateHistoryIndex,
} from "./services/ps5-history-index-client.js?v=1.1.2";

import {
  getHistoryNavigation,
} from "./services/ps5-history-navigation.js?v=1.1.2";

import { PS5HistoryClient } from "./services/ps5-history-client.js?v=1.1.2";

import {
  formatDuration,
  formatSensorHours,
  formatPeriod,
  shiftPeriod,
  getCurrentPeriod,
} from "./services/ps5-formatters.js?v=1.1.2";

import {
  createGameLibrary,
} from "./components/ps5-game-library.js?v=1.1.2";

import { PS5DailyHistoryClient } from "./services/ps5-daily-history-client.js?v=1.1.2";

import { compareGamingSeconds, aggregateDays, formatSessionCount } from "./services/ps5-first-row-metrics.js?v=1.1.2";

import { PS5LiveClient } from "./services/ps5-live-client.js?v=1.1.2";

/**
 * Optional local panoramic artwork, keyed by exact PlayStation title ID.
 *
 * Files are served by Home Assistant under /local/ps5-dashboard.
 * The original game cover is never stretched into a panoramic background.
 * Missing files fall back to the built-in PlayStation gradient.
 */
const GAME_BACKGROUNDS = Object.freeze({
  "PPSA17221_00": "/local/ps5-dashboard/assets/backgrounds/PPSA17221_00.webp",
});

const ENTITY_PREFIX = "sensor.ps5_monitoring_service_ps5_";

const ENTITIES = Object.freeze({
  consoleToday: `${ENTITY_PREFIX}console_today`,
  gamingToday: `${ENTITY_PREFIX}player_gaming_today`,
  gamingMonth: `${ENTITY_PREFIX}player_gaming_this_month`,
  sessions: `${ENTITY_PREFIX}player_monthly_sessions`,
  topGame: `${ENTITY_PREFIX}player_top_game`,
  history: `${ENTITY_PREFIX}player_annual_history`,
  library: `${ENTITY_PREFIX}player_game_library`,
});

const STYLES = `
:host{display:block;color:#eef5ff;font-family:Inter,system-ui,"Segoe UI",sans-serif}*{box-sizing:border-box}.dashboard{padding:22px;border-radius:22px;background:radial-gradient(ellipse at 85% -10%,#174789,transparent 45%),linear-gradient(145deg,#07182e,#030a17);border:1px solid #225085;box-shadow:0 24px 60px #0006}.header{display:flex;justify-content:space-between;align-items:center;padding-bottom:16px;margin-bottom:16px;border-bottom:1px solid #27486f}.heading{font-size:27px;font-weight:850;letter-spacing:-1px}.subtitle{font-size:11px;letter-spacing:1.6px;color:#8fb7e7;margin-top:5px}.symbols{font-size:24px;letter-spacing:8px;color:#278aff}.hero-grid{display:grid;grid-template-columns:1.25fr 1fr;gap:14px;margin-bottom:14px}.hero{min-height:205px;display:flex;align-items:center;gap:18px;padding:20px;background:linear-gradient(110deg,#113363,#0a1b36);border:1px solid #168cff;border-radius:17px}.hero img{width:110px;height:145px;object-fit:cover;border-radius:12px}.hero-title{font-size:clamp(23px,3vw,36px);font-weight:800;margin:8px 0}.eyebrow{font-size:11px;color:#90baf1;text-transform:uppercase;letter-spacing:1px}.state-pill{display:inline-block;border:1px solid #4c729e;border-radius:20px;padding:7px 10px;font-size:12px;background:#071b34;color:#c6d7ef}.hero-note{font-size:12px;color:#a2b9d7;margin-top:12px;line-height:1.6}.metrics{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.metric,.panel{background:linear-gradient(145deg,#102b4e,#091b32);border:1px solid #28517d;border-radius:16px;padding:17px}.metric-label{font-size:12px;color:#a2bbda}.metric-value{font-size:clamp(20px,2vw,30px);font-weight:800;margin-top:12px}.analytics-grid{display:grid;grid-template-columns:1.5fr 1fr;gap:14px;margin-bottom:14px}.bottom-grid{display:grid;grid-template-columns:1fr 1.5fr;gap:14px}.panel{min-width:0}.section-title{font-size:16px;font-weight:750;margin-bottom:15px}.panel-head{display:flex;justify-content:space-between;align-items:center;gap:10px}.tabs{display:flex;gap:4px}.tabs button{font-size:11px;padding:6px 9px}.tabs .active{background:#0878ec}.chart-bars{display:flex;align-items:flex-end;gap:3px;height:170px;border-bottom:1px solid #42628a;background:repeating-linear-gradient(to top,transparent 0,transparent 40px,#31517455 41px)}.chart-col{flex:1;min-width:2px;height:100%;display:flex;align-items:flex-end}.chart-bar{width:100%;min-height:2px;border-radius:3px 3px 0 0;background:linear-gradient(#28b7ff,#086ee8)}.chart-labels{display:flex;justify-content:space-between;font-size:11px;color:#9eb6d4;margin-top:10px}.donut-row{display:flex;align-items:center;gap:18px;min-height:185px}.donut{width:140px;height:140px;flex-shrink:0;border-radius:50%;background:conic-gradient(#149bff 0 var(--fill,0%),#294467 var(--fill,0%) 100%);display:grid;place-items:center}.donut-hole{width:100px;height:100px;border-radius:50%;background:#0a203b;display:flex;flex-direction:column;align-items:center;justify-content:center}.donut-total{font-size:21px;font-weight:800}.donut-legend{font-size:12px;line-height:2}.month-navigation{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:12px}.month-summary{display:flex;justify-content:space-between;padding:9px 0;border-bottom:1px solid #29466b;font-size:13px}.muted{color:#9fb6d5;font-size:12px}.error{color:#ffaaaa;font-size:12px}button{cursor:pointer;border:1px solid #365b88;background:#17365a;color:white;padding:9px 12px;border-radius:9px;font:inherit}button:hover{background:#235a9b}button:disabled{opacity:.35;cursor:not-allowed}.footer-note{font-size:11px;color:#8ba8c8;margin-top:14px}@media(max-width:900px){.hero-grid,.analytics-grid,.bottom-grid{grid-template-columns:1fr}}@media(max-width:560px){.dashboard{padding:12px}.symbols{display:none}.hero{padding:12px}.hero img{width:78px;height:105px}.metric{padding:12px}.donut-row{flex-wrap:wrap}}
 .live-active{border-color:#20d77a;color:#73ffae;background:#073822} 
.chart-legend{font-size:12px;color:#b9d5f4;margin:10px 0}.chart-col{position:relative;cursor:help}.chart-stack{display:flex;flex-direction:column-reverse;width:100%;overflow:hidden;border-radius:4px 4px 0 0}.chart-gaming{background:linear-gradient(#29baff,#0871ed)}.chart-idle{background:#56d5d7}.chart-tooltip{position:absolute;z-index:8;bottom:calc(100% + 8px);left:50%;transform:translateX(-50%);display:none;white-space:pre-line;width:max-content;max-width:280px;padding:12px;border:1px solid #5291d1;background:#07172c;border-radius:10px;font-size:12px;line-height:1.8;box-shadow:0 12px 30px #0009;pointer-events:none}.chart-col:hover .chart-tooltip,.chart-col:focus .chart-tooltip{display:block}.chart-col:first-child .chart-tooltip{left:0;transform:none}.chart-col:last-child .chart-tooltip{left:auto;right:0;transform:none}.title-list{display:grid;gap:9px;max-height:290px;overflow-y:auto;margin-top:12px}.title-row{display:grid;grid-template-columns:42px minmax(0,1fr) auto;align-items:center;gap:12px;padding:9px;background:#153152;border:1px solid #294e7d;border-radius:11px}.title-row img{width:42px;height:53px;object-fit:cover;border-radius:6px}.title-track{height:5px;border-radius:4px;background:#26466e;overflow:hidden;margin-top:7px}.title-fill{height:100%;background:#168fff}.timeline{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:5px;margin:12px 0}.timeline-month{text-align:center;padding:8px 2px;border:1px solid #2a4c75;border-radius:8px;color:#a9c5e5;min-width:0}.timeline-month strong{display:block;font-size:10px;white-space:nowrap;margin-bottom:8px}.timeline-month.selected{background:#1d4777;border-color:#269aff;color:#fff}.timeline-mark{height:4px;background:#667c94;border-radius:4px}.timeline-mark.gaming{background:#148fff}.timeline-mark.console{background:#56d5d7}.tabs{flex-wrap:wrap}


/* v1.1.0: Approved PlayStation first-row design; lower panels unchanged. */
.hero-grid{grid-template-columns:minmax(0,1.18fr) minmax(0,1fr);gap:14px;align-items:stretch}
.hero{position:relative;isolation:isolate;min-height:300px;overflow:hidden;display:flex;gap:22px;align-items:center;padding:22px 24px;border:1px solid #148cff;border-radius:22px;background:linear-gradient(125deg,#06172e,#0a2c60 85%);box-shadow:inset 0 0 28px #147bff24,0 0 18px #007aff30,0 14px 30px #0006}
.hero:after{content:"";position:absolute;pointer-events:none;inset:auto 0 0;height:4px;background:linear-gradient(90deg,#0066f6,#17c6ff);box-shadow:0 0 18px #00aaff}
.hero-backdrop{position:absolute;inset:0;z-index:-1;background-size:cover;background-position:center 36%;opacity:.58;filter:saturate(1.3)}
.hero-cover{width:clamp(96px,11vw,155px)!important;height:clamp(142px,16vw,216px)!important;flex-shrink:0;object-fit:cover;border-radius:14px!important;box-shadow:0 15px 32px #000b;border:1px solid #7bb8ff40}
.hero-copy{flex:1;min-width:0}
.hero .state-pill{display:inline-flex;align-items:center;gap:7px;font-size:clamp(12px,1vw,15px);font-weight:750;padding:8px 14px;border-radius:999px;background:#05182be8}
.hero .state-pill.live-active{background:#002c1bcf;color:#4bff83;border:1px solid #16e46c;box-shadow:0 0 15px #00e06530}
.hero-title{font-size:clamp(24px,2.45vw,42px);line-height:1.13;font-weight:850;margin:14px 0 8px;text-shadow:0 3px 15px #0008}
.hero-subtitle{color:#b4cce9;font-size:clamp(12px,1.15vw,17px)}
.hero-details{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:0;border-top:1px solid #72a7e744;margin-top:19px;padding-top:15px}
.hero-detail{display:flex;gap:9px;align-items:center;padding:0 12px;min-width:0;border-right:1px solid #4275b077}
.hero-detail:first-child{padding-left:0}.hero-detail:last-child{border-right:0;padding-right:0}
.hero-detail-icon{font-size:clamp(19px,1.8vw,30px);color:#4b9dff;line-height:1}
.hero-detail-copy{min-width:0}
.hero-detail-label{color:#b2c9e9;font-size:clamp(10px,.83vw,13px);line-height:1.4}
.hero-detail-value{font-size:clamp(15px,1.35vw,23px);font-weight:800;line-height:1.4}
.hero-detail-value.detail-positive{color:#36ff76}
.hero-note{font-size:10px;margin-top:10px;opacity:.8}
.metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px}
.metric{display:flex;flex-direction:column;min-width:0;min-height:300px;padding:22px 18px;border:1px solid var(--metric-accent);border-radius:20px;background:linear-gradient(160deg,#0b2a50,#05172f 80%);box-shadow:inset 0 1px 16px #2b89ff12,0 12px 24px #0005}
.metric:nth-child(3){background:linear-gradient(160deg,#211b55,#0b1731)}
.metric-icon{color:var(--metric-accent);font-size:clamp(31px,3.1vw,52px);line-height:1.1;font-weight:600;text-shadow:0 0 14px var(--metric-accent);margin-bottom:18px}
.metric-label{font-size:clamp(13px,1.12vw,19px);line-height:1.3;color:#c0d7f1}
.metric-value{font-size:clamp(23px,2.3vw,40px);line-height:1.15;margin-top:14px;white-space:nowrap;letter-spacing:-.7px}
.metric-footnote{margin-top:auto;padding-top:14px;color:#8bb1de;font-size:clamp(10px,.85vw,13px)}
@media(max-width:1120px){.hero-grid{grid-template-columns:1fr}.hero,.metric{min-height:245px}}
@media(max-width:700px){.metrics{grid-template-columns:repeat(3,minmax(0,1fr));gap:7px}.metric{min-height:175px;padding:12px 9px}.metric-icon{font-size:27px;margin-bottom:12px}.metric-value{font-size:clamp(16px,4vw,25px)}.metric-label{font-size:12px}.metric-footnote{font-size:10px}.hero{padding:14px;gap:12px;min-height:240px}.hero-cover{width:85px!important;height:119px!important}.hero-details{gap:4px}.hero-detail{padding:0 5px;gap:4px}.hero-detail-icon{font-size:17px}.hero-detail-label{font-size:10px}.hero-detail-value{font-size:14px}}
@media(max-width:420px){.hero{align-items:flex-start;flex-wrap:wrap}.hero-copy{flex-basis:calc(100% - 105px)}.hero-details{grid-template-columns:1fr;gap:7px}.hero-detail{border:0;padding:0}}
/* v1.1.2: approved first-row refinement. All lower panels remain unchanged. */
.hero-grid{grid-template-columns:minmax(0,1.18fr) minmax(0,1fr);gap:13px}
.hero{min-height:310px;border:1.5px solid #159cff;box-shadow:inset 0 0 24px #006aff28,0 0 20px #008cff50,0 15px 34px #0007}
.hero-backdrop{opacity:.7}
.hero-title{font-size:clamp(25px,2.45vw,42px)}
.hero-detail-value{font-size:clamp(16px,1.45vw,24px)}
.metrics{grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.metric{position:relative;min-height:310px;padding:20px 17px 15px;overflow:hidden;
 background:radial-gradient(ellipse at 85% -10%,color-mix(in srgb,var(--metric-accent) 24%,transparent),transparent 62%),linear-gradient(165deg,#0b2c54,#06162e 85%);
 border:1.5px solid var(--metric-accent);box-shadow:inset 0 0 24px #0589ff20,0 0 14px color-mix(in srgb,var(--metric-accent) 23%,transparent)}
.metric:nth-child(3){background:radial-gradient(ellipse at 85% -10%,#943cff75,transparent 65%),linear-gradient(165deg,#241456,#0c1434 85%)}
.metric:after{content:"";position:absolute;inset:auto 0 0;height:3px;background:var(--metric-accent);box-shadow:0 0 14px var(--metric-accent)}
.metric-icon{margin-bottom:13px;filter:drop-shadow(0 0 9px var(--metric-accent))}
.metric-icon svg{width:48px;height:48px;display:block}
.metric-label{font-size:clamp(14px,1.15vw,19px);font-weight:650}
.metric-value{font-size:clamp(27px,2.3vw,41px);margin-top:12px}
.metric-comparison{margin-top:16px;font-size:clamp(11px,.88vw,14px);font-weight:650;line-height:1.5;min-height:40px;color:#9fb7d5}
.metric-comparison.trend-up{color:#46ff84}.metric-comparison.trend-down{color:#ff8f96}
.metric-comparison.trend-new{color:#75d7f7}.metric-comparison.trend-neutral{color:#a9c4de}
.metric-bottom{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:auto;padding-top:13px;
 border-top:1px solid color-mix(in srgb,var(--metric-accent) 42%,transparent);font-size:clamp(11px,.9vw,14px);font-weight:650}
@media(max-width:1120px){.hero-grid{grid-template-columns:1fr}.hero,.metric{min-height:245px}}
@media(max-width:700px){.metric{min-height:200px;padding:13px 9px}.metric-icon svg{width:30px;height:30px}.metric-comparison{font-size:10px;min-height:55px}.metric-bottom{flex-wrap:wrap;font-size:10px}}

`;
function createElement(tag, className, text) {
  const element = document.createElement(tag);

  if (className) {
    element.className = className;
  }

  if (text !== undefined) {
    element.textContent = String(text);
  }

  return element;
}

class PS5DashboardCard extends HTMLElement {
  constructor() {
    super();

    this.attachShadow({ mode: "open" });

    this._hass = null;
    this._client = null;

    // The historical index client manages its own MQTT
    // subscription through the existing HA WebSocket.
    this._indexClient = null;
    this._liveClient = null;
    this._backgroundRequest = 0;
    this._backgroundTitleId = null;
    this._liveState = null;
    this._liveError = null;
    this._heroElements = null;
    this._historyIndex = null;
    this._gamingPeriods = [];
    this._indexLoading = true;
    this._indexError = null;
    this._navigationElements = null;

    this._config = {};
    this._period = getCurrentPeriod();

    // Track the local calendar month independently from
    // the month currently selected in the dashboard.
    this._calendarPeriod = this._period;
    this._rolloverReloadPending = false;

    this._history = null;
    this._loading = false;
    this._error = null;
    this._controller = null;
    this._requestGeneration = 0;
    this._chartMode = 12;
    this._dailyClient = null;
    this._dailyHistory = null;
    this._dailyError = null;
    this._dailyLoading = false;
    this._dailyRequestGeneration = 0;
    this._dailyController = null;
    // Independent weekly total: never reuse or overwrite chart data.
    this._weeklySeconds = null;
    this._weeklyDate = null;
    this._weeklyRequestedAt = 0;
    this._weeklyGeneration = 0;
    this._weeklyAbort = null;
    this._weeklyPending = false;
    this._comparison = { yesterday: null, previousWeek: null, todaySessions: null, weekSessions: null };
    this._comparisonDate = null;
    this._comparisonRequestedAt = 0;
    this._comparisonPending = false;
    this._comparisonGeneration = 0;
    this._comparisonAbort = null;
  }

  setConfig(config) {
    this._config = config || {};
    this._render();
  }

  set hass(hass) {
    this._hass = hass;

    // Detect a calendar-month rollover using the regular
    // Home Assistant update cycle.
    this._checkCalendarRollover();

    if (this._client) {
      this._client.updateHass(hass);
    } else {
      this._client = new PS5HistoryClient(hass);
    }

    // Keep the index subscription independent from monthly
    // historical requests and regular HA state updates.
    if (this._indexClient) {
      const previousConnection = this._indexClient.hass.connection;

      this._indexClient.updateHass(hass);

      if (previousConnection !== hass.connection) {
        this._historyIndex = null;
        this._gamingPeriods = [];
        this._indexLoading = true;
        this._indexError = null;

        // Invalidate controls that were based on the
        // previous Home Assistant connection.
        this._updateNavigation();

        this._connectHistoryIndex();
      }
    } else {
      this._indexClient = new PS5HistoryIndexClient(
        hass,
        (validated) => this._onHistoryIndex(validated),
      );

      this._connectHistoryIndex();
    }

    // Maintain an independent subscription to the retained live-state feed.
    if (this._liveClient) {
      const previousConnection = this._liveClient.hass.connection;
      this._liveClient.updateHass(hass);
      if (previousConnection !== hass.connection) {
        this._liveState = null;
        this._liveError = null;
        this._updateLiveHero();
        this._connectLive();
      }
    } else {
      this._liveClient = new PS5LiveClient(
        hass,
        (live) => this._onLiveState(live),
      );
      this._connectLive();
    }

    // Daily requests share the authenticated Home Assistant connection.
    if (this._dailyClient) {
      const changed = this._dailyClient.hass.connection !== hass.connection;
      this._dailyClient.updateHass(hass);
      if (changed) {
        this._weeklyGeneration++;
        this._weeklyAbort?.abort();
        this._weeklyAbort = null;
        this._weeklyPending = false;
        this._weeklyRequestedAt = 0;
        this._weeklySeconds = null;
        this._comparisonGeneration++;
        this._comparisonAbort?.abort();
        this._comparisonAbort = null;
        this._comparisonPending = false;
        this._comparisonRequestedAt = 0;
        this._comparison = { yesterday: null, previousWeek: null, todaySessions: null, weekSessions: null };
        this._cancelDailyHistory();
        this._dailyHistory = null;
        if (this._chartMode === "week" || this._chartMode === "month") {
          void this._loadDailyHistory();
        }
      }
    } else {
      this._dailyClient = new PS5DailyHistoryClient(hass);
      if (this._chartMode === "week" || this._chartMode === "month") {
        void this._loadDailyHistory();
      }
    }

    // Refresh the current calendar week's confirmed gaming total.
    // Limit polling to avoid generating MQTT traffic on every HA update.
    this._refreshWeeklyMetric();
    this._refreshComparisons();

    // Update existing metric elements without rebuilding
    // the complete Shadow DOM on every Home Assistant update.
    if (this._metricsInitialized) {
      this._updateMetrics();
    } else {
      this._render();
    }

    if (this._rolloverReloadPending) {
      this._rolloverReloadPending = false;
      void this._loadMonth();
    } else if (
      !this._history &&
      !this._loading &&
      !this._error
    ) {
      void this._loadMonth();
    }
  }

  /**
   * Invalidate the cached index when the local month changes.
   *
   * Historical data remains available through the monthly
   * request client, but navigation waits for a fresh index.
   */
  _checkCalendarRollover() {
    const current = getCurrentPeriod();

    if (current === this._calendarPeriod) {
      return;
    }

    const previousCalendarPeriod = this._calendarPeriod;

    this._calendarPeriod = current;

    // Follow the current month only when the user was
    // already viewing the previous current month.
    if (this._period === previousCalendarPeriod) {
      this._period = current;
      this._history = null;
      this._error = null;

      // Defer the request until the hass setter has
      // updated the MQTT client dependencies.
      this._rolloverReloadPending = true;
    }

    this._historyIndex = null;
    this._gamingPeriods = [];
    this._indexLoading = true;
    this._indexError = null;

    this._updateNavigation();
  }

  connectedCallback() {
    // Restore MQTT clients when the card is reinserted
    // without waiting for another Home Assistant update.
    if (this._hass) {
      this.hass = this._hass;
    } else {
      this._render();
    }
  }

  disconnectedCallback() {
    this._requestGeneration += 1;
    this._controller?.abort();
    this._controller = null;
    this._client?.dispose();
    this._client = null;

    this._cancelDailyHistory();
    this._weeklyGeneration++;
    this._weeklyAbort?.abort();
    this._weeklyAbort = null;
    this._weeklyPending = false;
    this._weeklySeconds = null;
    this._weeklyDate = null;
    this._comparisonGeneration++;
    this._comparisonAbort?.abort();
    this._comparisonAbort = null;
    this._comparisonPending = false;
    this._dailyClient?.dispose();
    this._dailyClient = null;
    this._dailyHistory = null;
    this._liveClient?.dispose();
    this._liveClient = null;
    this._liveState = null;
    this._liveError = null;
    this._heroElements = null;

    // Release the independent index subscription.
    this._indexClient?.dispose();
    this._indexClient = null;

    this._historyIndex = null;
    this._gamingPeriods = [];
    this._indexLoading = true;
    this._indexError = null;

    // Navigation elements belong to the current Shadow DOM.
    // They must not survive a card disconnection.
    this._navigationElements = null;
  }

  /** Connect to the live feed without affecting historical requests. */
  _connectLive() {
    const client = this._liveClient;
    if (!client) return;
    void client.connect().catch((error) => {
      if (this._liveClient !== client) return;
      this._liveError = "Live-state connection unavailable";
      this._updateLiveHero();
      console.warn("PS5 live-state subscription failed:", error);
    });
  }

  /** Apply only the newest accepted live state to the hero elements. */
  _onLiveState(live) {
    if (!this.isConnected) return;
    this._liveState = live;
    this._liveError = null;
    this._updateLiveHero();
  }

  /**
   * Retrieve a Monday-to-today gaming total from the existing daily MQTT
   * protocol. The data is independently cached from the chart's requests.
   * Do not invent a weekly total when the broker is unavailable.
   */
  _refreshWeeklyMetric() {
    if (!this._dailyClient || !this.isConnected) return;
    const now = new Date();
    const localDate = [
      now.getFullYear(),
      String(now.getMonth() + 1).padStart(2, "0"),
      String(now.getDate()).padStart(2, "0"),
    ].join("-");
    if (this._weeklyDate !== localDate) {
      this._weeklyGeneration++;
      this._weeklyAbort?.abort();
      this._weeklyAbort = null;
      this._weeklyPending = false;
      this._weeklySeconds = null;
      this._weeklyDate = localDate;
      this._weeklyRequestedAt = 0;
    }
    if (this._weeklyPending || Date.now() - this._weeklyRequestedAt < 60000) return;
    this._weeklyPending = true;
    this._weeklyRequestedAt = Date.now();
    const generation = ++this._weeklyGeneration;
    const controller = new AbortController();
    this._weeklyAbort = controller;
    const mondayOffset = (now.getDay() + 6) % 7;
    const monday = new Date(now.getFullYear(), now.getMonth(),
      now.getDate() - mondayOffset);
    const tomorrow = new Date(now.getFullYear(), now.getMonth(),
      now.getDate() + 1);
    const format = date => [
      date.getFullYear(),
      String(date.getMonth() + 1).padStart(2, "0"),
      String(date.getDate()).padStart(2, "0"),
    ].join("-");
    void this._dailyClient.getDays(format(monday), format(tomorrow), {
      signal: controller.signal,
    }).then(response => {
      if (generation !== this._weeklyGeneration) return;
      const weekly = aggregateDays(response.days);
      this._weeklySeconds = weekly.gaming_seconds;
      this._comparison.weekSessions = weekly.gaming_sessions;
      this._updateMetrics();
    }).catch(error => {
      if (generation === this._weeklyGeneration && error.name !== "AbortError") {
        console.warn("PS5 weekly statistics unavailable:", error);
      }
    }).finally(() => {
      if (generation === this._weeklyGeneration) {
        this._weeklyPending = false;
        this._weeklyAbort = null;
      }
    });
  }

  /** Fetch yesterday and the previous Monday-Sunday week for comparisons. */
  _refreshComparisons() {
    if (!this._dailyClient || !this.isConnected) return;
    const now = new Date();
    const day = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const format = d => [d.getFullYear(), String(d.getMonth()+1).padStart(2,"0"),
      String(d.getDate()).padStart(2,"0")].join("-");
    const dateKey = format(day);
    if (this._comparisonDate !== dateKey) {
      this._comparisonGeneration++;
      this._comparisonAbort?.abort();
      this._comparison = { yesterday: null, previousWeek: null, todaySessions: null, weekSessions: null };
      this._comparisonDate = dateKey;
      this._comparisonPending = false;
      this._comparisonRequestedAt = 0;
    }
    if (this._comparisonPending || Date.now()-this._comparisonRequestedAt < 300000) return;
    this._comparisonPending = true;
    this._comparisonRequestedAt = Date.now();
    const generation = ++this._comparisonGeneration;
    const controller = new AbortController();
    this._comparisonAbort = controller;
    const offset = n => new Date(day.getFullYear(), day.getMonth(), day.getDate()+n);
    const mondayOffset = (day.getDay()+6)%7;
    const requests = [
      this._dailyClient.getDays(format(offset(-1)), format(offset(1)), {signal:controller.signal}),
      this._dailyClient.getDays(format(offset(-mondayOffset-7)), format(offset(-mondayOffset)), {signal:controller.signal}),
    ];
    void Promise.allSettled(requests).then(results => {
      if (generation !== this._comparisonGeneration) return;
      if (results[0].status === "fulfilled") {
        this._comparison.yesterday = results[0].value.days[0]?.gaming_seconds ?? null;
        this._comparison.todaySessions = results[0].value.days[1]?.gaming_sessions ?? null;
      }
      if (results[1].status === "fulfilled") {
        this._comparison.previousWeek = aggregateDays(results[1].value.days).gaming_seconds;
      }
      this._updateMetrics();
    }).finally(() => {
      if (generation === this._comparisonGeneration) {
        this._comparisonPending = false;
        this._comparisonAbort = null;
      }
    });
  }

  /** Update the live panel in place, preserving charts and metrics. */
  _updateLiveHero() {
    const elements = this._heroElements;
    if (!elements) return;
    const live = this._liveState;
    const stale = !live || !live.available ||
      Date.now() - Date.parse(live.observed_at) > 90000;
    let status = "Sem comunicação";
    if (!stale) {
      if (!live.console_active) status = "Consola desligada";
      else if (live.player_gaming) status = "● A jogar agora";
      else status = "● Consola ligada";
    }
    elements.status.textContent = this._liveError ?? status;
    elements.status.className = "state-pill" + (!stale && live.player_gaming ? " live-active" : "");
    elements.title.textContent = !stale && live.player_gaming
      ? (live.title_name || "Jogo não identificado")
      : (!stale && live.console_active ? "PlayStation 5" : "Último jogo: " + (this._history?.games?.[0]?.title_name ?? "—"));
    // The v0.5.0 live payload does not contain a confirmed session
    // start time. Do not use observed_at as a session start timestamp.
    elements.start.textContent = "—";
    elements.duration.textContent = "—";
    elements.power.textContent = stale ? "Desconhecido"
      : (live.console_active ? "Ligada" : "Desligada");
    elements.power.className = "hero-detail-value" +
      (!stale && live.console_active ? " detail-positive" : "");
    elements.note.textContent = !live
      ? "À espera do estado MQTT da PS5…"
      : `Última atualização: ${new Date(live.observed_at).toLocaleTimeString("pt-PT")}. ` +
        "Início e duração aguardam confirmação do backend.";
    const image = !stale && live.player_gaming ? live.title_image : this._history?.games?.[0]?.title_image;
    if (image && /^https:\/\//.test(image)) {
      elements.cover.src = image;
      elements.cover.alt = `${elements.title.textContent} cover`;
      elements.cover.hidden = false;
    } else {
      elements.cover.hidden = true;

    }
    this._updateGameBackground(
      !stale && live.player_gaming ? live.title_id : null,
    );
  }

  /**
   * Load optional local panoramic artwork without stretching cover art.
   * Ignore outdated asynchronous image loads when the current game changes.
   */
  _updateGameBackground(titleId) {
    const elements = this._heroElements;
    if (!elements) return;
    const normalized = typeof titleId === "string" ? titleId : null;
    if (normalized === this._backgroundTitleId) return;
    this._backgroundTitleId = normalized;
    const request = ++this._backgroundRequest;
    const path = normalized && GAME_BACKGROUNDS[normalized];
    elements.backdrop.style.backgroundImage = "none";
    if (!path) return;
    const image = new Image();
    image.onload = () => {
      if (request !== this._backgroundRequest) return;
      elements.backdrop.style.backgroundImage =
        `linear-gradient(90deg,#08162bf5 0%,#08162bd9 44%,#08162b55 100%),url("${path}")`;
    };
    image.onerror = () => {
      if (request === this._backgroundRequest) {
        elements.backdrop.style.backgroundImage = "none";
      }
    };
    image.src = path;
  }

  /**
   * Establish the independent historical index subscription.
   *
   * Repeated connection attempts reuse the same client
   * subscription promise.
   */
  _connectHistoryIndex() {
    if (!this._indexClient) {
      return;
    }

    const client = this._indexClient;

    void client.connect().catch((error) => {
      if (this._indexClient !== client) {
        return;
      }

      this._indexLoading = false;
      this._indexError = error.message;

      this._updateNavigation();

      console.warn(
        "PS5 historical index subscription failed:",
        error,
      );
    });
  }

  /**
   * Accept a validated historical index update.
   *
   * The index may arrive through a retained MQTT message
   * or a subsequent backend publication.
   */
  _onHistoryIndex(validated) {
    if (!this.isConnected) {
      return;
    }

    try {
      const result = validateHistoryIndex(validated.index);

      // Never replace a newer index with an older retained
      // publication from the same calendar window.
      if (this._historyIndex) {
        const previousTime = Date.parse(
          this._historyIndex.generated_at,
        );

        const incomingTime = Date.parse(
          result.index.generated_at,
        );

        if (incomingTime < previousTime) {
          return;
        }
      }

      this._historyIndex = result.index;
      this._gamingPeriods = result.gamingPeriods;
      this._indexLoading = false;
      this._indexError = null;

      // Refresh navigation controls without rebuilding
      // metrics, charts, or the Game Library.
      this._updateNavigation();
      this._updateActivityChart();
      this._updateMetrics();

    } catch (error) {
      this._indexError = error.message;
      this._indexLoading = false;
      this._updateNavigation();
    }
  }

  async _loadMonth() {
    if (!this._client) {
      return;
    }

    this._requestGeneration += 1;
    const generation = this._requestGeneration;

    this._controller?.abort();
    this._controller = new AbortController();

    this._loading = true;
    this._error = null;
    this._history = null;
    this._render();

    try {
      const response = await this._client.getMonth(
        this._period,
        { signal: this._controller.signal },
      );

      if (generation !== this._requestGeneration) {
        return;
      }

      this._history = response;
    } catch (error) {
      if (generation !== this._requestGeneration) {
        return;
      }

      if (error.name !== "AbortError") {
        this._error = error.message;
      }
    } finally {
      if (generation === this._requestGeneration) {
        this._loading = false;
        this._render();
      }
    }
  }

  /**
   * Return the currently valid historical navigation targets.
   *
   * The current month remains accessible even without
   * confirmed gaming sessions.
   */
  _getNavigationTargets() {
    const currentPeriod = getCurrentPeriod();

    if (!this._historyIndex) {
      return {
        previous: null,
        next: null,
      };
    }

    try {
      const validated = validateHistoryIndex(
        this._historyIndex,
      );

      const navigation = getHistoryNavigation(
        validated.gamingPeriods,
        this._period,
      );

      // Never navigate into future calendar months.
      if (
        navigation.next &&
        navigation.next > currentPeriod
      ) {
        navigation.next = null;
      }

      // Always allow returning to the current month
      // from a previously selected gaming month.
      if (
        this._period < currentPeriod &&
        (
          navigation.next === null ||
          navigation.next > currentPeriod
        )
      ) {
        navigation.next = currentPeriod;
      }

      return navigation;

    } catch (error) {
      return {
        previous: null,
        next: null,
      };
    }
  }

  /**
   * Navigate to the nearest month with confirmed gaming.
   *
   * Months without gaming are skipped automatically.
   */
  _changeMonth(offset) {
    if (![-1, 1].includes(offset)) {
      return;
    }

    const navigation = this._getNavigationTargets();

    const next = offset < 0
      ? navigation.previous
      : navigation.next;

    if (!next || next === this._period) {
      return;
    }

    this._period = next;

    this._updateNavigation();
    void this._loadMonth();
  }

  /**
   * Update the navigation controls without rebuilding
   * the dashboard or replacing metric DOM elements.
   */
  _updateNavigation() {
    if (!this._navigationElements) {
      return;
    }

    const navigation = this._getNavigationTargets();

    const {
      previous,
      next,
      label,
      status,
    } = this._navigationElements;

    previous.disabled = !navigation.previous;
    next.disabled = !navigation.next;

    label.textContent = formatPeriod(this._period);
    this._updateTimeline();

    // Update the status independently from the monthly
    // history panel and all existing metric elements.
    if (status) {
      const hasValidIndex = Boolean(
        this._historyIndex &&
        !this._indexError &&
        !this._indexLoading
      );

      if (hasValidIndex) {
        status.textContent = "";
      } else if (this._indexError) {
        status.textContent = "History navigation unavailable";
      } else {
        status.textContent = "Loading history navigation…";
      }

      status.hidden = hasValidIndex;
    }
  }

  /** Show adjacent months even when smart navigation skips empty months. */
  _updateTimeline() {
    if (!this._timelineContainer) return;
    this._timelineContainer.replaceChildren();
    const index = new Map((this._historyIndex?.months ?? []).map(item => [item.month, item]));
    for (const offset of [-4,-3,-2,-1,0]) {
      const period = shiftPeriod(this._period, offset);
      const item = index.get(period);
      const cell = createElement("div", "timeline-month" + (offset === 0 ? " selected" : ""));
      cell.append(createElement("strong", "", formatPeriod(period)));
      cell.append(createElement("div", "timeline-mark" + (item?.has_gaming ? " gaming" : item?.has_activity ? " console" : "")));
      cell.title = !item ? "Fora do histórico" : item.has_gaming ? "Gaming confirmado" : item.has_activity ? "Consola ligada sem gaming" : "Sem atividade registada";
      this._timelineContainer.append(cell);
    }
  }

  _entityState(key) {
    return this._hass?.states?.[ENTITIES[key]]?.state;
  }

  /**
   * Update metric values without rebuilding the dashboard.
   *
   * Home Assistant may update the hass property frequently.
   * Only changed text values are written to the DOM.
   */
  _updateMetrics() {
    if (!this._metricElements) {
      return;
    }

    const todayHours = Number(this._entityState("gamingToday"));
    const monthHours = Number(this._entityState("gamingMonth"));
    const todaySeconds = Number.isFinite(todayHours) && todayHours >= 0 ? todayHours*3600 : null;
    const monthSeconds = Number.isFinite(monthHours) && monthHours >= 0 ? monthHours*3600 : null;
    const current = getCurrentPeriod();
    const previousMonth = this._historyIndex?.months?.find(
      item => item.month === shiftPeriod(current, -1));
    const sessions = Number(this._entityState("sessions"));
    const games = this._period === current && Array.isArray(this._history?.games)
      ? this._history.games.length : null;
    const values = new Map([
      ["Hoje", {value:formatSensorHours(this._entityState("gamingToday")),
        comparison:compareGamingSeconds(todaySeconds,this._comparison.yesterday,"ontem"),
        sessions:formatSessionCount(this._comparison.todaySessions)}],
      ["Esta semana", {value:this._weeklySeconds === null ? "—" : formatDuration(this._weeklySeconds),
        comparison:compareGamingSeconds(this._weeklySeconds,this._comparison.previousWeek,"semana anterior"),
        sessions:formatSessionCount(this._comparison.weekSessions)}],
      ["Este mês", {value:formatSensorHours(this._entityState("gamingMonth")),
        comparison:compareGamingSeconds(monthSeconds,previousMonth?.gaming_seconds ?? null,"mês anterior"),
        sessions:formatSessionCount(sessions),
        games:Number.isInteger(games) ? `${games} ${games === 1 ? "jogo" : "jogos"}` : "Jogos indisponíveis"}],
    ]);
    for (const [label, metric] of values) {
      const value = this._metricElements.get(label);
      if (!value) continue;
      value.textContent = metric.value;
      const extra = this._metricExtras?.get(label);
      if (!extra) continue;
      extra.comparison.textContent = metric.comparison.text;
      extra.comparison.className = "metric-comparison trend-" + metric.comparison.trend;
      extra.sessions.textContent = metric.sessions;
      if (extra.games) extra.games.textContent = metric.games;
    }
  }

  _render() {
    if (!this.shadowRoot) return;
    this._metricsInitialized = false;
    this._metricElements = null;
    this._metricExtras = null;
    this.shadowRoot.replaceChildren();
    const style = document.createElement("style");
    style.textContent = STYLES;
    this.shadowRoot.append(style);
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "/local/ps5-dashboard/styles/ps5-game-library.css?v=1.1.2";
    this.shadowRoot.append(link);
    const dashboard = createElement("div", "dashboard");
    const header = createElement("div", "header");
    const brand = createElement("div");
    brand.append(createElement("div", "heading", "PS5  |  Gaming Analytics"), createElement("div", "subtitle", "PLAYER · PLAYSTATION MONITOR"));
    header.append(brand, createElement("div", "symbols", "△ ○ × □"));
    dashboard.append(header);
    // Only the first dashboard row is redesigned in v1.1.0.
    // The existing charts, navigation, library and history remain intact.
    const heroGrid = createElement("div", "hero-grid");
    const hero = createElement("section", "hero");
    const backdrop = createElement("div", "hero-backdrop");
    backdrop.setAttribute("aria-hidden", "true");
    hero.append(backdrop);
    const cover = document.createElement("img");
    cover.className = "hero-cover";
    cover.hidden = true;
    hero.append(cover);

    const heroText = createElement("div", "hero-copy");
    const liveStatus = createElement("div", "state-pill", "A aguardar MQTT");
    const title = createElement("div", "hero-title", "PlayStation 5");
    const subtitle = createElement("div", "hero-subtitle", "PS5 · Jogo em execução");
    const details = createElement("div", "hero-details");

    const detail = (symbol, label, initial) => {
      const item = createElement("div", "hero-detail");
      item.append(createElement("span", "hero-detail-icon", symbol));
      const body = createElement("div", "hero-detail-copy");
      body.append(createElement("div", "hero-detail-label", label));
      const value = createElement("div", "hero-detail-value", initial);
      body.append(value);
      item.append(body);
      details.append(item);
      return value;
    };
    const startValue = detail("◷", "Início da sessão", "—");
    const durationValue = detail("◷", "Duração (em tempo real)", "—");
    const powerValue = detail("🎮", "Estado da PS5", "Desconhecido");
    const note = createElement("div", "hero-note", "À espera do estado MQTT da PS5…");
    heroText.append(liveStatus, title, subtitle, details, note);
    hero.append(heroText);
    this._heroElements = {
      cover, backdrop, title, status: liveStatus, note,
      start: startValue, duration: durationValue, power: powerValue,
    };
    this._updateLiveHero();
    heroGrid.append(hero);

    const metrics = createElement("div", "metrics");
    const values = [
      ["Hoje", "gamepad", "#35baff"],
      ["Esta semana", "calendar", "#39e7e6"],
      ["Este mês", "calendar", "#c07bff"],
    ];
    this._metricElements = new Map();
    this._metricExtras = new Map();
    for (const [name, iconType, accent] of values) {
      const metric = createElement("section", "metric");
      metric.style.setProperty("--metric-accent", accent);
      const icon = createElement("div", "metric-icon");
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.setAttribute("viewBox", "0 0 24 24");
      svg.setAttribute("fill", "none");
      svg.setAttribute("stroke", "currentColor");
      svg.setAttribute("stroke-width", "1.8");
      svg.setAttribute("stroke-linecap", "round");
      svg.setAttribute("stroke-linejoin", "round");
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", iconType === "gamepad"
        ? "M6 12h4m-2-2v4m7-2h.01M18 10h.01M6.5 6h11a4 4 0 0 1 3.9 3.1l1 5a3 3 0 0 1-4.7 3L15 15H9l-2.7 2.1a3 3 0 0 1-4.7-3l1-5A4 4 0 0 1 6.5 6Z"
        : "M8 2v4m8-4v4M3 10h18M5 4h14a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Zm3 10h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01");
      svg.append(path);
      icon.append(svg);
      metric.append(icon, createElement("div", "metric-label", name));
      const number = createElement("div", "metric-value", "—");
      const comparison = createElement("div", "metric-comparison trend-unknown", "Comparação indisponível");
      const footer = createElement("div", "metric-bottom");
      const sessions = createElement("span", "metric-session", "Sessões indisponíveis");
      footer.append(sessions);
      let games = null;
      if (name === "Este mês") {
        games = createElement("span", "metric-games", "Jogos indisponíveis");
        footer.prepend(games);
      }
      metric.append(number, comparison, footer);
      this._metricElements.set(name, number);
      this._metricExtras.set(name, {comparison,sessions,games});
      metrics.append(metric);
    }
    this._metricsInitialized = true;
    heroGrid.append(metrics);
    dashboard.append(heroGrid);
    this._updateMetrics();
    const analytics=createElement("div","analytics-grid");
    const activity=createElement("section","panel");
    const chartHead=createElement("div","panel-head");
    chartHead.append(createElement("div","section-title","Gaming activity"));
    const tabs=createElement("div","tabs");
    for(const [name,mode] of [["Semana","week"],["Mês","month"],["6 meses",6],["12 meses",12],["2 anos",24],["3 anos",36]]) {
      const tab=createElement("button",(this._chartMode??12)===mode?"active":"",name);
      tab.addEventListener("click",()=>{
        this._chartMode = mode;
        for (const child of tabs.children) child.className = child===tab?"active":"";
        if (mode === "week" || mode === "month") {
          void this._loadDailyHistory();
        } else {
          this._cancelDailyHistory();
          this._updateActivityChart();
        }
      });
      tabs.append(tab);
    }
    chartHead.append(tabs);activity.append(chartHead);
    this._chartContainer=createElement("div");activity.append(this._chartContainer);analytics.append(activity);
    const distribution = createElement("section", "panel");
    distribution.append(createElement("div", "section-title", "Jogos mais utilizados · mês selecionado"));
    const games = [...(this._history?.games ?? [])].sort((a,b)=>b.duration_seconds-a.duration_seconds);
    const total = games.reduce((sum,g)=>sum+g.duration_seconds,0);
    const list = createElement("div", "title-list");
    if (!games.length) list.append(createElement("p", "muted", "Sem jogos confirmados neste mês."));
    for (const game of games) {
      const percent = total ? game.duration_seconds/total*100 : 0;
      const row = createElement("div", "title-row");
      const cover = createElement("img");
      if (typeof game.title_image === "string" && game.title_image.startsWith("https://")) {
        cover.src = game.title_image; cover.alt = game.title_name; cover.loading = "lazy";
      } else cover.hidden = true;
      const info = createElement("div");
      info.append(createElement("strong", "", game.title_name));
      info.append(createElement("div", "muted", `${formatDuration(game.duration_seconds)} · ${game.session_count} sessões`));
      const track = createElement("div", "title-track");
      const fill = createElement("div", "title-fill"); fill.style.width = `${percent}%`;track.append(fill);info.append(track);
      row.append(cover, info, createElement("strong", "", `${percent.toFixed(1)}%`));list.append(row);
    }
    distribution.append(createElement("div", "muted", `Total confirmado: ${formatDuration(total)}`),list);
    analytics.append(distribution);dashboard.append(analytics);
    const bottom=createElement("div","bottom-grid");
    const history=createElement("section","panel");
    history.append(createElement("div","section-title","Monthly history"));
    const navigation=createElement("div","month-navigation");
    const previous=createElement("button","","←");previous.addEventListener("click",()=>this._changeMonth(-1));
    const next=createElement("button","","→");next.addEventListener("click",()=>this._changeMonth(1));
    const label=createElement("strong","",formatPeriod(this._period));navigation.append(previous,label,next);
    const status=createElement("p","muted","");status.setAttribute("role","status");status.setAttribute("aria-live","polite");
    this._navigationElements={previous,next,label,status};history.append(navigation,status);this._timelineContainer=createElement("div","timeline");history.append(this._timelineContainer);this._updateNavigation();
    if(this._loading)history.append(createElement("p","muted","Loading historical statistics…"));
    else if(this._error)history.append(createElement("p","error",this._error));
    else if(this._history){for(const [name,value] of [["Gaming time",formatDuration(this._history.summary.gaming_seconds)],["Console time",formatDuration(this._history.summary.console_seconds)],["Sessions",String(this._history.summary.gaming_sessions)],["Games",String(this._history.games.length)]]){const row=createElement("div","month-summary");row.append(createElement("span","",name),createElement("strong","",value));history.append(row);}}
    bottom.append(history);
    const library=createElement("section","panel");library.append(createElement("div","section-title","Game library · selected month"));
    if(this._history)library.append(createGameLibrary(this._history.games));
    else library.append(createElement("p","muted","Waiting for game statistics…"));
    bottom.append(library);dashboard.append(bottom);
    dashboard.append(createElement("div","footer-note","Estatísticas confirmadas · estado da consola via MQTT em tempo real"));
    this.shadowRoot.append(dashboard);this._updateActivityChart();this._updateLiveHero();
  }

  /**
   * Cancel stale daily requests before switching chart periods or connections.
   */
  _cancelDailyHistory() {
    this._dailyRequestGeneration += 1;
    this._dailyController?.abort();
    this._dailyController = null;
    this._dailyLoading = false;
  }

  /**
   * Calculate a local calendar window without assuming a fixed UTC offset.
   */
  _getDailyWindow() {
    const now = new Date();
    const end = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
    const start = this._chartMode === "week"
      ? new Date(now.getFullYear(), now.getMonth(), now.getDate() - 6)
      : new Date(now.getFullYear(), now.getMonth(), 1);
    const format = date => [
      date.getFullYear(),
      String(date.getMonth() + 1).padStart(2, "0"),
      String(date.getDate()).padStart(2, "0"),
    ].join("-");
    return { start: format(start), end: format(end) };
  }

  /**
   * Load daily statistics only for the selected daily chart mode.
   */
  async _loadDailyHistory() {
    if (!this._dailyClient ||
        !["week", "month"].includes(this._chartMode)) return;
    this._cancelDailyHistory();
    const generation = this._dailyRequestGeneration;
    const controller = new AbortController();
    this._dailyController = controller;
    this._dailyLoading = true;
    this._dailyError = null;
    this._dailyHistory = null;
    this._updateActivityChart();

    try {
      const { start, end } = this._getDailyWindow();
      const response = await this._dailyClient.getDays(start, end, {
        signal: controller.signal,
      });
      if (generation !== this._dailyRequestGeneration) return;
      this._dailyHistory = response;
    } catch (error) {
      if (generation !== this._dailyRequestGeneration) return;
      if (error.name !== "AbortError") this._dailyError = error.message;
    } finally {
      if (generation === this._dailyRequestGeneration) {
        this._dailyLoading = false;
        this._updateActivityChart();
      }
    }
  }

  /** Render stacked confirmed gaming and non-gaming console durations. */
  _updateActivityChart() {
    if (!this._chartContainer) return;
    this._chartContainer.replaceChildren();
    if (this._chartMode === "week" || this._chartMode === "month") {
      if (this._dailyLoading) {
        this._chartContainer.append(createElement("p","muted","A carregar atividade diária…"));
        return;
      }
      if (this._dailyError || !this._dailyHistory) {
        this._chartContainer.append(createElement("p","muted",
          this._dailyError
            ? `Histórico diário indisponível: ${this._dailyError}`
            : "À espera do histórico diário MQTT…"));
        return;
      }
      this._renderDailyChart(this._dailyHistory.days);
      return;
    }
    const months = this._historyIndex?.months;
    if (!Array.isArray(months) || months.length !== 36) {
      this._chartContainer.append(createElement("p","muted","À espera do índice histórico MQTT…"));return;
    }
    const selected = months.slice(-(this._chartMode ?? 12));
    const max = Math.max(1,...selected.map(m=>Math.max(m.console_seconds??0,m.gaming_seconds??0)));
    const legend = createElement("div","chart-legend","■ Gaming (azul)    ■ Consola ligada sem gaming (turquesa)");
    this._chartContainer.append(legend);
    const bars = createElement("div","chart-bars");
    for (const item of selected) {
      const consoleSeconds = Math.max(0,item.console_seconds??0);
      const gamingSeconds = Math.max(0,item.gaming_seconds??0);
      const idle = Math.max(0,consoleSeconds-gamingSeconds);
      const total = Math.max(consoleSeconds,gamingSeconds);
      const column = createElement("div","chart-col");column.tabIndex=0;
      const stack = createElement("div","chart-stack");stack.style.height=`${total>0?Math.max(2,total/max*100):0}%`;
      const gaming = createElement("div","chart-gaming");gaming.style.height=`${total?gamingSeconds/total*100:0}%`;
      const nongaming = createElement("div","chart-idle");nongaming.style.height=`${total?idle/total*100:0}%`;
      stack.append(gaming,nongaming);
      const tip = createElement("div","chart-tooltip",`${item.month}\nConsola: ${formatDuration(consoleSeconds)}\nGaming: ${formatDuration(gamingSeconds)}\nSem gaming: ${formatDuration(idle)}`);
      if (item.month === this._period && this._history?.games) {
        for (const game of this._history.games) tip.append(createElement("div","",`${game.title_name}: ${formatDuration(game.duration_seconds)}`));
      }
      column.append(stack,tip);bars.append(column);
    }
    this._chartContainer.append(bars);
    const labels = createElement("div","chart-labels");labels.append(createElement("span","",selected[0].month),createElement("span","",selected.at(-1).month));this._chartContainer.append(labels);
    this._chartContainer.append(createElement("p","muted","Totais mensais confirmados · coloca o rato sobre uma coluna"));
  }

  /**
   * Render daily bars with confirmed console and gaming durations.
   * Every bar exposes its games through a keyboard-accessible tooltip.
   */
  _renderDailyChart(days) {
    const max = Math.max(1, ...days.map(day => day.console_seconds));
    const legend = createElement("div", "chart-legend",
      "■ Gaming (azul)    ■ Consola ligada sem gaming (turquesa)");
    this._chartContainer.append(legend);
    const bars = createElement("div", "chart-bars");
    for (const day of days) {
      const total = day.console_seconds;
      const gamingSeconds = day.gaming_seconds;
      const idle = Math.max(0, total - gamingSeconds);
      const column = createElement("div", "chart-col");
      column.tabIndex = 0;
      column.setAttribute("aria-label",
        `${day.date}: ${formatDuration(gamingSeconds)} gaming`);
      const stack = createElement("div", "chart-stack");
      stack.style.height = `${total ? Math.max(2, total / max * 100) : 0}%`;
      const gaming = createElement("div", "chart-gaming");
      gaming.style.height = `${total ? gamingSeconds / total * 100 : 0}%`;
      const nongaming = createElement("div", "chart-idle");
      nongaming.style.height = `${total ? idle / total * 100 : 0}%`;
      stack.append(gaming, nongaming);
      const tooltip = createElement("div", "chart-tooltip",
        `${day.date}\nConsola: ${formatDuration(total)}\nGaming: ${formatDuration(gamingSeconds)}\nSem gaming: ${formatDuration(idle)}`);
      for (const game of [...day.games].sort(
        (a,b) => b.duration_seconds - a.duration_seconds)) {
        tooltip.append(createElement("div", "",
          `${game.title_name}: ${formatDuration(game.duration_seconds)}`));
      }
      column.append(stack, tooltip);
      bars.append(column);
    }
    this._chartContainer.append(bars);
    if (days.length) {
      const labels = createElement("div", "chart-labels");
      labels.append(createElement("span", "", days[0].date),
        createElement("span", "", days.at(-1).date));
      this._chartContainer.append(labels);
    }
  }

  getCardSize() {
    return 8;
  }
}

if (!customElements.get("ps5-dashboard-card")) {
  customElements.define("ps5-dashboard-card", PS5DashboardCard);
}

window.customCards = window.customCards || [];

if (
  !window.customCards.some(
    (card) => card.type === "ps5-dashboard-card",
  )
) {
  window.customCards.push({
    type: "ps5-dashboard-card",
    name: "PS5 Dashboard",
    description: "PlayStation gaming analytics dashboard.",
    preview: false,
  });
}
