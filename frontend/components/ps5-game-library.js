/**
 * PS5 Dashboard - Game Library Component.
 *
 * Render monthly game statistics using native DOM APIs.
 *
 * Features:
 * - Responsive game cards.
 * - PlayStation cover artwork.
 * - Confirmed gaming duration.
 * - Session counts.
 * - Relative playtime indicators.
 * - Empty library presentation.
 *
 * All displayed values originate from the validated
 * historical response supplied by the parent component.
 */

import {
  formatDuration,
} from "../services/ps5-formatters.js?v=1.0.5";

/**
 * Create an HTML element with optional class and text.
 *
 * Text is assigned through textContent to avoid
 * interpreting game metadata as HTML.
 *
 * @param {string} tag
 * @param {string} className
 * @param {string} text
 * @returns {HTMLElement}
 */
function createElement(tag, className = "", text = "") {
  const element = document.createElement(tag);

  if (className) {
    element.className = className;
  }

  element.textContent = text;

  return element;
}

/**
 * Build a game library DOM element.
 *
 * @param {Array<object>} games
 * @returns {HTMLElement}
 */
export function createGameLibrary(games) {
  if (!Array.isArray(games)) {
    throw new TypeError("Game library must be an array.");
  }

  const library = createElement("div", "ps5-game-library");

  if (games.length === 0) {
    library.append(
      createElement(
        "p",
        "ps5-library-empty",
        "No gaming activity recorded for this month.",
      ),
    );

    return library;
  }

  // Preserve the source collection while sorting games
  // by their confirmed gaming duration.
  const ordered = [...games].sort(
    (a, b) => b.duration_seconds - a.duration_seconds,
  );

  const maximumDuration = Math.max(
    ...ordered.map((game) => game.duration_seconds),
    0,
  );

  for (const game of ordered) {
    const card = createElement("article", "ps5-game-card");

    const artwork = createElement(
      "div",
      "ps5-game-artwork",
    );

    if (
      typeof game.title_image === "string" &&
      /^https:\/\//i.test(game.title_image)
    ) {
      const image = document.createElement("img");

      image.src = game.title_image;
      image.alt = `${game.title_name} cover`;
      image.loading = "lazy";
      image.decoding = "async";
      image.referrerPolicy = "no-referrer";

      artwork.append(image);
    } else {
      artwork.append(
        createElement(
          "div",
          "ps5-game-placeholder",
          "PS5",
        ),
      );
    }

    const content = createElement(
      "div",
      "ps5-game-content",
    );

    content.append(
      createElement(
        "div",
        "ps5-game-title",
        game.title_name,
      ),
      createElement(
        "div",
        "ps5-game-duration",
        formatDuration(game.duration_seconds),
      ),
      createElement(
        "div",
        "ps5-game-sessions",
        `${game.session_count} ${
          game.session_count === 1 ? "session" : "sessions"
        }`,
      ),
    );

    const progress = createElement(
      "div",
      "ps5-game-progress",
    );

    const progressFill = createElement(
      "div",
      "ps5-game-progress-fill",
    );

    const percentage =
      maximumDuration > 0
        ? (game.duration_seconds / maximumDuration) * 100
        : 0;

    progressFill.style.width = `${Math.min(
      100,
      Math.max(0, percentage),
    )}%`;

    progress.append(progressFill);
    content.append(progress);

    card.append(artwork, content);
    library.append(card);
  }

  return library;
}
