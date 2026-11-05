/**
 * PS5 Dashboard - Presentation Formatters.
 *
 * Pure utility functions for calendar navigation, durations,
 * and numerical presentation.
 *
 * No Home Assistant or browser dependencies are required.
 */

export const MONTH_NAMES = Object.freeze([
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
]);

/**
 * Format confirmed duration in seconds.
 *
 * @param {number} seconds
 * @returns {string}
 */
export function formatDuration(seconds) {
  if (
    typeof seconds !== "number" ||
    !Number.isFinite(seconds) ||
    seconds < 0
  ) {
    return "—";
  }

  const totalMinutes = Math.round(seconds / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  return `${hours}h ${String(minutes).padStart(2, "0")}m`;
}

/**
 * Format decimal hours from Home Assistant sensors.
 *
 * @param {string|number} value
 * @returns {string}
 */
export function formatSensorHours(value) {
  if (
    value === null ||
    value === undefined ||
    value === "" ||
    value === "unknown" ||
    value === "unavailable"
  ) {
    return "—";
  }

  const hours = Number(value);

  if (!Number.isFinite(hours) || hours < 0) {
    return "—";
  }

  return formatDuration(hours * 3600);
}

/**
 * Format a YYYY-MM period for display.
 *
 * @param {string} period
 * @returns {string}
 */
export function formatPeriod(period) {
  if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(period)) {
    return "Invalid period";
  }

  const [year, month] = period.split("-").map(Number);

  return `${MONTH_NAMES[month - 1]} ${year}`;
}

/**
 * Shift a calendar month without timezone-dependent parsing.
 *
 * @param {string} period
 * @param {number} offset
 * @returns {string}
 */
export function shiftPeriod(period, offset) {
  const [year, month] = period.split("-").map(Number);

  const absoluteMonth = year * 12 + month - 1 + offset;

  const nextYear = Math.floor(absoluteMonth / 12);
  const nextMonth = ((absoluteMonth % 12) + 12) % 12 + 1;

  return `${nextYear}-${String(nextMonth).padStart(2, "0")}`;
}

/**
 * Return the current local calendar period.
 *
 * @returns {string}
 */
export function getCurrentPeriod() {
  const now = new Date();

  return `${now.getFullYear()}-${String(
    now.getMonth() + 1,
  ).padStart(2, "0")}`;
}
