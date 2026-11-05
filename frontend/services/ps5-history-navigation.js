/**
 * PS5 Dashboard - Intelligent History Navigation.
 *
 * Navigate through calendar months with confirmed gaming
 * activity while preserving the complete 36-month index.
 *
 * This module performs no network requests and does not
 * modify Home Assistant state.
 */

const PERIOD_PATTERN = /^\d{4}-(0[1-9]|1[0-2])$/;

/**
 * Validate and extract navigable gaming months.
 *
 * @param {object} index - Historical activity index.
 * @returns {string[]} Chronologically ordered gaming periods.
 */
export function getGamingPeriods(index) {
  if (
    !index ||
    index.schema_version !== 1 ||
    index.month_count !== 36 ||
    !Array.isArray(index.months) ||
    index.months.length !== 36
  ) {
    throw new Error("Invalid historical activity index.");
  }

  const periods = [];
  let previous = null;

  for (const entry of index.months) {
    if (
      !entry ||
      typeof entry.month !== "string" ||
      !PERIOD_PATTERN.test(entry.month) ||
      typeof entry.has_gaming !== "boolean"
    ) {
      throw new Error("Invalid historical month entry.");
    }

    const [year, month] = entry.month.split("-").map(Number);
    const absoluteMonth = year * 12 + month - 1;

    if (
      previous !== null &&
      absoluteMonth !== previous + 1
    ) {
      throw new Error(
        "Historical months must be consecutive."
      );
    }

    previous = absoluteMonth;

    if (entry.has_gaming) {
      periods.push(entry.month);
    }
  }

  return periods;
}

/**
 * Find the nearest navigable month in one direction.
 *
 * @param {string[]} periods - Sorted gaming periods.
 * @param {string} currentPeriod - Currently displayed month.
 * @param {number} direction - Either -1 or 1.
 * @returns {string|null} Target month or null.
 */
export function findAdjacentGamingPeriod(
  periods,
  currentPeriod,
  direction,
) {
  if (
    !Array.isArray(periods) ||
    !PERIOD_PATTERN.test(currentPeriod) ||
    ![-1, 1].includes(direction)
  ) {
    throw new Error("Invalid navigation arguments.");
  }

  if (direction < 0) {
    for (let index = periods.length - 1; index >= 0; index--) {
      if (periods[index] < currentPeriod) {
        return periods[index];
      }
    }

    return null;
  }

  for (const period of periods) {
    if (period > currentPeriod) {
      return period;
    }
  }

  return null;
}

/**
 * Return navigation availability for the current month.
 *
 * @param {string[]} periods - Navigable gaming periods.
 * @param {string} currentPeriod - Displayed calendar month.
 * @returns {object} Previous and next navigation targets.
 */
export function getHistoryNavigation(
  periods,
  currentPeriod,
) {
  return {
    previous: findAdjacentGamingPeriod(
      periods,
      currentPeriod,
      -1,
    ),
    next: findAdjacentGamingPeriod(
      periods,
      currentPeriod,
      1,
    ),
  };
}
