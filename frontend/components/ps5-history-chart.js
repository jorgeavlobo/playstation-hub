/**
 * PS5 Dashboard - Annual History Chart.
 *
 * Render a responsive SVG chart using confirmed monthly
 * PlayStation statistics from Home Assistant.
 *
 * No third-party charting libraries are required.
 *
 * Responsibilities:
 * - Validate the monthly statistics collection.
 * - Preserve chronological month ordering.
 * - Compare console and Player gaming durations.
 * - Scale the vertical axis automatically.
 * - Display all twelve calendar months.
 * - Provide accessible chart descriptions.
 */

const SVG_NAMESPACE = "http://www.w3.org/2000/svg";

const CHART_WIDTH = 720;
const CHART_HEIGHT = 260;

const MARGIN = Object.freeze({
  top: 25,
  right: 20,
  bottom: 48,
  left: 48,
});

const CONSOLE_COLOR = "#478BFF";
const GAMING_COLOR = "#54D5BD";
const GRID_COLOR = "#34445D";
const LABEL_COLOR = "#9BAFCC";

/**
 * Create an SVG element with attributes.
 *
 * @param {string} tag
 * @param {object} attributes
 * @returns {SVGElement}
 */
function createSVGElement(tag, attributes = {}) {
  const element = document.createElementNS(
    SVG_NAMESPACE,
    tag,
  );

  for (const [name, value] of Object.entries(attributes)) {
    element.setAttribute(name, String(value));
  }

  return element;
}

/**
 * Validate and normalize monthly statistics.
 *
 * @param {Array<object>} months
 * @returns {Array<object>}
 */
export function normalizeHistory(months) {
  if (!Array.isArray(months)) {
    throw new TypeError(
      "Annual history must be an array.",
    );
  }

  const normalized = months.map((entry) => {
    if (
      !entry ||
      typeof entry.month !== "string" ||
      !/^\d{4}-(0[1-9]|1[0-2])$/.test(entry.month)
    ) {
      throw new Error(
        "Invalid annual history calendar month.",
      );
    }

    for (const field of [
      "console_hours",
      "gaming_hours",
      "gaming_sessions",
    ]) {
      const value = entry[field];

      if (
        typeof value !== "number" ||
        !Number.isFinite(value) ||
        value < 0
      ) {
        throw new Error(
          `Invalid annual history field: ${field}`,
        );
      }
    }

    if (!Number.isInteger(entry.gaming_sessions)) {
      throw new Error(
        "Gaming sessions must be an integer.",
      );
    }

    return {
      month: entry.month,
      console_hours: entry.console_hours,
      gaming_hours: entry.gaming_hours,
      gaming_sessions: entry.gaming_sessions,
    };
  });

  normalized.sort(
    (a, b) => a.month.localeCompare(b.month),
  );

  if (normalized.length !== 12) {
    throw new Error(
      "Annual history must contain exactly twelve months.",
    );
  }

  const uniqueMonths = new Set(
    normalized.map((entry) => entry.month),
  );

  if (uniqueMonths.size !== normalized.length) {
    throw new Error(
      "Annual history contains duplicate months.",
    );
  }

  return normalized;
}

/**
 * Calculate a readable upper limit for the chart axis.
 *
 * @param {Array<object>} months
 * @returns {number}
 */
export function calculateAxisMaximum(months) {
  const maximum = Math.max(
    0,
    ...months.flatMap((entry) => [
      entry.console_hours,
      entry.gaming_hours,
    ]),
  );

  if (maximum === 0) {
    return 1;
  }

  const magnitude = Math.pow(
    10,
    Math.floor(Math.log10(maximum)),
  );

  const normalized = maximum / magnitude;

  const step =
    normalized <= 2 ? 0.5 :
    normalized <= 5 ? 1 :
    2;

  return Math.ceil(normalized / step) * step * magnitude;
}

/**
 * Create the annual history chart.
 *
 * @param {Array<object>} history
 * @returns {HTMLElement}
 */
export function createHistoryChart(history) {
  const months = normalizeHistory(history);

  const container = document.createElement("div");
  container.className = "ps5-history-chart";

  const svg = createSVGElement("svg", {
    viewBox: `0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`,
    role: "img",
    "aria-label": (
      "PlayStation console and Player gaming hours " +
      "during the last twelve months"
    ),
    preserveAspectRatio: "xMidYMid meet",
  });

  svg.style.width = "100%";
  svg.style.height = "auto";
  svg.style.display = "block";

  const plotWidth =
    CHART_WIDTH - MARGIN.left - MARGIN.right;

  const plotHeight =
    CHART_HEIGHT - MARGIN.top - MARGIN.bottom;

  const maximum = calculateAxisMaximum(months);

  // Draw horizontal grid lines and numerical labels.
  for (let index = 0; index <= 4; index += 1) {
    const fraction = index / 4;

    const y =
      MARGIN.top + plotHeight * (1 - fraction);

    const value = maximum * fraction;

    svg.append(
      createSVGElement("line", {
        x1: MARGIN.left,
        y1: y,
        x2: CHART_WIDTH - MARGIN.right,
        y2: y,
        stroke: GRID_COLOR,
        "stroke-dasharray": "4 5",
      }),
    );

    const label = createSVGElement("text", {
      x: MARGIN.left - 10,
      y: y + 4,
      fill: LABEL_COLOR,
      "font-size": 12,
      "text-anchor": "end",
    });

    label.textContent = value.toFixed(1);
    svg.append(label);
  }

  const groupWidth = plotWidth / months.length;
  const barWidth = Math.min(16, groupWidth * 0.3);

  for (const [index, month] of months.entries()) {
    const centerX =
      MARGIN.left +
      groupWidth * index +
      groupWidth / 2;

    const values = [
      {
        hours: month.console_hours,
        color: CONSOLE_COLOR,
        offset: -barWidth,
      },
      {
        hours: month.gaming_hours,
        color: GAMING_COLOR,
        offset: 1,
      },
    ];

    for (const value of values) {
      const height =
        (value.hours / maximum) * plotHeight;

      svg.append(
        createSVGElement("rect", {
          x: centerX + value.offset,
          y: MARGIN.top + plotHeight - height,
          width: barWidth - 1,
          height,
          rx: 3,
          fill: value.color,
        }),
      );
    }

    const label = createSVGElement("text", {
      x: centerX,
      y: CHART_HEIGHT - 20,
      fill: LABEL_COLOR,
      "font-size": 12,
      "text-anchor": "middle",
    });

    const [, monthNumber] = month.month.split("-");

    label.textContent = [
      "Jan", "Feb", "Mar", "Apr",
      "May", "Jun", "Jul", "Aug",
      "Sep", "Oct", "Nov", "Dec",
    ][Number(monthNumber) - 1];

    svg.append(label);
  }

  container.append(svg);

  return container;
}
