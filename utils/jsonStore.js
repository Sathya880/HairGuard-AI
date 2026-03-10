/**
 * jsonStore.js
 * Path: backend/node/utils/jsonStore.js
 *
 * Reads/writes the two JSON "databases":
 *   - data/hairKnowledge.json   (read-only seed data)
 *   - data/userIntelligence.json (read-write user progress)
 *
 * The data/ folder is expected to be a sibling of this utils/ folder:
 *   backend/node/
 *     ├── utils/
 *     │     └── jsonStore.js   ← this file
 *     └── data/
 *           ├── hairKnowledge.json
 *           └── userIntelligence.json
 */

const fs   = require("fs");
const path = require("path");

// ── Resolve data directory relative to THIS file (not process.cwd()) ─────────
const DATA_DIR          = path.join(__dirname, "..", "data");
const KNOWLEDGE_FILE    = path.join(DATA_DIR, "hairKnowledge.json");
const INTELLIGENCE_FILE = path.join(DATA_DIR, "userIntelligence.json");

// ── Ensure data dir + files exist ────────────────────────────────────────────
function ensureFiles() {
  if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
    console.log("[jsonStore] Created data directory:", DATA_DIR);
  }
  if (!fs.existsSync(KNOWLEDGE_FILE)) {
    fs.writeFileSync(KNOWLEDGE_FILE, "[]", "utf8");
    console.warn("[jsonStore] WARNING: hairKnowledge.json was missing — created empty file at:", KNOWLEDGE_FILE);
    console.warn("[jsonStore] ACTION REQUIRED: Place your seed data JSON at that path.");
  }
  if (!fs.existsSync(INTELLIGENCE_FILE)) {
    fs.writeFileSync(INTELLIGENCE_FILE, "{}", "utf8");
    console.log("[jsonStore] Created empty userIntelligence.json at:", INTELLIGENCE_FILE);
  }
}

// ── Hair Knowledge (categories + facts) ──────────────────────────────────────
function readKnowledge() {
  ensureFiles();
  try {
    const raw = fs.readFileSync(KNOWLEDGE_FILE, "utf8");
    const parsed = JSON.parse(raw);

    if (!Array.isArray(parsed)) {
      console.error("[jsonStore] hairKnowledge.json must be an array of category objects. Got:", typeof parsed);
      return [];
    }

    const activeCount = parsed.filter((c) => c.isActive).length;
    const totalFacts  = parsed.reduce((acc, c) => acc + (c.facts?.length || 0), 0);
    console.log(`[jsonStore] Loaded hairKnowledge: ${parsed.length} categories, ${activeCount} active, ${totalFacts} total facts`);

    return parsed;
  } catch (err) {
    console.error("[jsonStore] Failed to read/parse hairKnowledge.json:", err.message);
    console.error("[jsonStore] File path:", KNOWLEDGE_FILE);
    return [];
  }
}

// ── User Intelligence (keyed by userId) ──────────────────────────────────────
function readAllIntel() {
  ensureFiles();
  try {
    const raw = fs.readFileSync(INTELLIGENCE_FILE, "utf8");
    const parsed = JSON.parse(raw);
    if (typeof parsed !== "object" || Array.isArray(parsed)) {
      console.error("[jsonStore] userIntelligence.json must be a plain object keyed by userId.");
      return {};
    }
    return parsed;
  } catch (err) {
    console.error("[jsonStore] Failed to read/parse userIntelligence.json:", err.message);
    return {};
  }
}

function writeAllIntel(data) {
  ensureFiles();
  try {
    fs.writeFileSync(INTELLIGENCE_FILE, JSON.stringify(data, null, 2), "utf8");
  } catch (err) {
    console.error("[jsonStore] Failed to write userIntelligence.json:", err.message);
    throw err;
  }
}

function getOrCreateIntel(userId) {
  if (!userId) throw new Error("User ID missing from request");
  const all = readAllIntel();
  if (!all[userId]) {
    console.log(`[jsonStore] Creating new intelligence record for user: ${userId}`);
    all[userId] = {
      userId,
      xp:                 0,
      factsRead:          0,
      mythsBusted:        0,
      totalQuizCorrect:   0,
      totalQuizAnswered:  0,
      dailySessions:      [],
      streak:             { days: 0, lastDate: null, longest: 0 },
      achievements:       [],
      categoriesExplored: [],
    };
    writeAllIntel(all);
  }
  return all[userId];
}

function saveIntel(userId, intel) {
  const all = readAllIntel();
  all[userId] = intel;
  writeAllIntel(all);
}

// ── Debug helper — call once on startup to verify paths ───────────────────────
function debugPaths() {
  console.log("=== jsonStore path check ===");
  console.log("DATA_DIR         :", DATA_DIR);
  console.log("KNOWLEDGE_FILE   :", KNOWLEDGE_FILE);
  console.log("INTELLIGENCE_FILE:", INTELLIGENCE_FILE);
  console.log("hairKnowledge exists    :", fs.existsSync(KNOWLEDGE_FILE));
  console.log("userIntelligence exists :", fs.existsSync(INTELLIGENCE_FILE));
  console.log("============================");
}

module.exports = { readKnowledge, getOrCreateIntel, saveIntel, debugPaths };