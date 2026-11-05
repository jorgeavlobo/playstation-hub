/**
 * PS5 Dashboard - Game Library Component Tests.
 *
 * Validate game ordering, artwork, durations, progress
 * indicators, and empty library handling.
 *
 * No browser, MQTT broker, or production data is required.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

/**
 * Provide a minimal DOM implementation for component tests.
 */
class FakeElement {
  constructor(tagName) {
    this.tagName = tagName;
    this.className = "";
    this.textContent = "";
    this.children = [];
    this.style = {};
  }

  append(...elements) {
    this.children.push(...elements);
  }
}

globalThis.document = {
  createElement(tagName) {
    return new FakeElement(tagName);
  },
};

/**
 * Load the formatter module first and replace the relative
 * import with an isolated data URL for Node.js execution.
 */
const formatterSource = await readFile(
  new URL("../services/ps5-formatters.js", import.meta.url),
  "utf8",
);

const formatterUrl = `data:text/javascript;base64,${
  Buffer.from(formatterSource).toString("base64")
}`;

let librarySource = await readFile(
  new URL("../components/ps5-game-library.js", import.meta.url),
  "utf8",
);

// Replace the formatter import regardless of its cache
// version. This keeps tests compatible with future releases.
const formatterImportPattern =
  /\.\.\/services\/ps5-formatters\.js\?v=\d+\.\d+\.\d+/g;

const formatterMatches = librarySource.match(
  formatterImportPattern,
);

if (!formatterMatches || formatterMatches.length !== 1) {
  throw new Error(
    "Expected exactly one versioned formatter import.",
  );
}

librarySource = librarySource.replace(
  formatterImportPattern,
  formatterUrl,
);

const libraryUrl = `data:text/javascript;base64,${
  Buffer.from(librarySource).toString("base64")
}`;

const { createGameLibrary } = await import(libraryUrl);

/**
 * Recursively find elements by CSS class.
 */
function findByClass(root, className) {
  const matches = [];

  if (root.className === className) {
    matches.push(root);
  }

  for (const child of root.children) {
    matches.push(...findByClass(child, className));
  }

  return matches;
}

function makeGame(name, seconds, sessions, image = null) {
  return {
    title_id: name,
    title_name: name,
    title_image: image,
    duration_seconds: seconds,
    session_count: sessions,
  };
}

test("rejects invalid game collections", () => {
  assert.throws(
    () => createGameLibrary(null),
    /Game library must be an array/,
  );
});

test("renders an empty library", () => {
  const library = createGameLibrary([]);

  const empty = findByClass(library, "ps5-library-empty");

  assert.equal(empty.length, 1);
  assert.match(empty[0].textContent, /No gaming activity/);
});

test("orders games by confirmed duration", () => {
  const games = [
    makeGame("Minecraft", 3600, 1),
    makeGame("Fortnite", 7200, 2),
    makeGame("Roblox", 1800, 1),
  ];

  const library = createGameLibrary(games);

  const titles = findByClass(library, "ps5-game-title");

  assert.deepEqual(
    titles.map((element) => element.textContent),
    ["Fortnite", "Minecraft", "Roblox"],
  );

  // The original statistics collection must not be mutated.
  assert.equal(games[0].title_name, "Minecraft");
});

test("renders game artwork and placeholders", () => {
  const games = [
    makeGame(
      "Minecraft",
      3600,
      1,
      "https://example.com/minecraft.png",
    ),
    makeGame("Unknown Game", 1200, 1),
  ];

  const library = createGameLibrary(games);

  const artwork = findByClass(library, "ps5-game-artwork");
  const placeholders = findByClass(
    library,
    "ps5-game-placeholder",
  );

  assert.equal(artwork.length, 2);
  assert.equal(placeholders.length, 1);

  assert.equal(artwork[0].children[0].tagName, "img");
  assert.equal(
    artwork[0].children[0].src,
    "https://example.com/minecraft.png",
  );
});

test("renders durations and session counts", () => {
  const library = createGameLibrary([
    makeGame("Minecraft", 5400, 2),
  ]);

  const durations = findByClass(
    library,
    "ps5-game-duration",
  );

  const sessions = findByClass(
    library,
    "ps5-game-sessions",
  );

  assert.equal(durations[0].textContent, "1h 30m");
  assert.equal(sessions[0].textContent, "2 sessions");
});

test("calculates proportional progress bars", () => {
  const library = createGameLibrary([
    makeGame("Minecraft", 7200, 2),
    makeGame("Roblox", 3600, 1),
  ]);

  const bars = findByClass(
    library,
    "ps5-game-progress-fill",
  );

  assert.equal(bars.length, 2);
  assert.equal(bars[0].style.width, "100%");
  assert.equal(bars[1].style.width, "50%");
});
