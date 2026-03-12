/**
 * hairKnowledge.js  (router)
 * Path: backend/node/routes/hairKnowledge.js
 *
 * All routes rewritten to use local JSON files — no MongoDB required.
 * Drop-in replacement for the original Mongoose-based router.
 */

const express = require("express");
const router  = express.Router();
const auth    = require("../middleware/auth");
const { readKnowledge, getOrCreateIntel, saveIntel } = require("../utils/jsonStore");
const mongoose          = require("mongoose");
const UserIntelligence  = require("../models/UserIntelligence");

// ─── XP / Level thresholds ───────────────────────────────────────────────────
const LEVELS = [
  { level: 1, name: "Hair Curious",    xpRequired: 0,    factsTarget: 6, quizTarget: 3 },
  { level: 2, name: "Follicle Finder", xpRequired: 100,  factsTarget: 6, quizTarget: 3 },
  { level: 3, name: "Scalp Scholar",   xpRequired: 250,  factsTarget: 7, quizTarget: 3 },
  { level: 4, name: "Growth Guru",     xpRequired: 500,  factsTarget: 7, quizTarget: 3 },
  { level: 5, name: "Keratin Keeper",  xpRequired: 900,  factsTarget: 6, quizTarget: 3 },
  { level: 6, name: "Hair Expert",     xpRequired: 1400, factsTarget: 7, quizTarget: 3 },
  { level: 7, name: "Trichology Pro",  xpRequired: 2100, factsTarget: 7, quizTarget: 3 },
];

const XP_PER_FACT       = 10;
const XP_PER_QUIZ_RIGHT = 20;
const XP_STREAK_BONUS   = 15;

// Per-level targets — resolved at runtime from the LEVELS table above.
// Rule: 6–7 facts per level → 3 quiz questions.
function getLevelConfig(levelNum) {
  return LEVELS.find((l) => l.level === levelNum) || LEVELS[LEVELS.length - 1];
}

// ─── Pure helpers ─────────────────────────────────────────────────────────────
function computeLevel(totalXp) {
  let current = LEVELS[0];
  for (const l of LEVELS) {
    if (totalXp >= l.xpRequired) current = l;
    else break;
  }
  const nextLevel    = LEVELS.find((l) => l.level === current.level + 1);
  const xpIntoLevel  = totalXp - current.xpRequired;
  const xpToNext     = nextLevel ? nextLevel.xpRequired - current.xpRequired : 0;
  return {
    currentLevel:  current.level,
    levelName:     current.name,
    xpToNextLevel: xpToNext,
    xpProgress:    xpIntoLevel,
  };
}

function todayStr() {
  return new Date().toISOString().split("T")[0];
}

function shuffle(arr) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

// ─── Enrich a fact with quiz options (myth busters get true/false options) ───
function enrichFact(fact, category) {
  const f = { ...fact, category };
  if (f.isMythBuster && f.mythStatement) {
    f.quizOptions = [
      { id: "true",  text: "✅ TRUE — this is accurate" },
      { id: "false", text: "❌ FALSE — this is a myth"  },
    ];
    f.correctAnswer = f.isTruth ? "true" : "false";
  }
  return f;
}

// ─── Collect facts from the new level-keyed knowledge structure ───────────────
// hairKnowledge.json is now: [ { level, factsTarget, quizTarget, facts[], quiz[] }, ... ]
function getLevelEntry(knowledge, levelNum) {
  return knowledge.find((entry) => entry.level === levelNum) || null;
}

// ─────────────────────────────────────────────────────────────────────────────
// GET /facts-for-level?level=N
// Returns: { level, facts[], quizFacts[], totalAvailable, factsTarget, quizTarget }
// Shape matches the new JSON: { level: N, facts: [...N facts...], quiz: [...N quiz...] }
// ─────────────────────────────────────────────────────────────────────────────
router.get("/facts-for-level", auth, (req, res) => {
  try {
    const userId = req.userId;
    const intel  = getOrCreateIntel(userId);
    const { currentLevel } = computeLevel(intel.xp || 0);

    // Use requested level directly — no cap so "go to previous level" works correctly.
    // If no level param is passed, use the user's current level.
    const requestedLevel = req.query.level
      ? parseInt(req.query.level, 10)
      : currentLevel;

    const knowledge = readKnowledge(); // now an array of level entries
    const cfg       = getLevelConfig(requestedLevel);

    // Find the matching level entry; fall back to nearest lower level
    let entry = getLevelEntry(knowledge, requestedLevel);
    if (!entry) {
      // Fallback: pick the highest available level ≤ requested
      const candidates = knowledge.filter((e) => e.level <= requestedLevel);
      entry = candidates.length ? candidates[candidates.length - 1] : knowledge[0];
    }

    const allFacts  = (entry.facts || []).map((f) => enrichFact(f, f.category || ""));
    const allQuiz   = (entry.quiz  || []).map((f) => enrichFact(f, f.category || ""));

    shuffle(allFacts);
    shuffle(allQuiz);

    const facts     = allFacts.slice(0, cfg.factsTarget);
    const quizFacts = allQuiz.slice(0,  cfg.quizTarget);

    res.json({
      success:        true,
      level:          requestedLevel,
      facts,
      quizFacts,
      totalAvailable: allFacts.length,
      factsTarget:    cfg.factsTarget,
      quizTarget:     cfg.quizTarget,
    });
  } catch (error) {
    console.error("facts-for-level error:", error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// GET /categories
// Derives a category view from the new level-keyed knowledge structure.
// ─────────────────────────────────────────────────────────────────────────────
router.get("/categories", auth, (req, res) => {
  try {
    const { severity, level } = req.query;
    const knowledge = readKnowledge(); // array of { level, facts[], quiz[] }

    // Flatten all facts across all levels into a category map
    const catMap = {};
    for (const entry of knowledge) {
      for (const fact of entry.facts || []) {
        const cat = fact.category || "Uncategorised";
        if (!catMap[cat]) catMap[cat] = [];
        let f = { ...fact };
        if (severity && f.severityLevel !== severity) continue;
        if (level    && entry.level > parseInt(level, 10)) continue;
        catMap[cat].push(enrichFact(f, cat));
      }
    }

    const result = Object.entries(catMap).map(([category, facts]) => ({
      category,
      facts,
      isActive: true,
    }));

    res.json({ success: true, categories: result });
  } catch (error) {
    console.error("Get categories error:", error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// GET /level
// ─────────────────────────────────────────────────────────────────────────────
// ─── Helper: rebuild local intel from a MongoDB UserIntelligence document ────
function _hydrateIntelFromMongo(userId, mongoDoc) {
  return {
    userId,
    xp:                 mongoDoc.xp                 || 0,
    factsRead:          mongoDoc.factsRead           || 0,
    mythsBusted:        mongoDoc.mythsBusted         || 0,
    totalQuizCorrect:   mongoDoc.totalQuizCorrect    || 0,
    totalQuizAnswered:  mongoDoc.totalQuizAnswered   || 0,
    streak: {
      days:     mongoDoc.streak?.days     || 0,
      lastDate: mongoDoc.streak?.lastDate || null,
      longest:  mongoDoc.streak?.longest  || 0,
    },
    achievements:       (mongoDoc.achievements       || []).map((a) => ({ ...a })),
    dailySessions:      (mongoDoc.dailySessions      || []).map((s) => ({ ...s })),
    categoriesExplored: (mongoDoc.categoriesExplored || []).map((c) => ({ ...c })),
  };
}

router.get("/level", auth, async (req, res) => {
  try {
    const userId = req.userId;
    let intel    = getOrCreateIntel(userId);

    // ── PERSISTENCE FIX: if local file lost data (server restart / ephemeral FS),
    //    recover from MongoDB which is the durable source of truth. ─────────────
    if ((intel.xp || 0) === 0) {
      try {
        const mongoDoc = await UserIntelligence.findOne({
          userId: new mongoose.Types.ObjectId(userId),
        }).lean();

        if (mongoDoc && (mongoDoc.xp || 0) > 0) {
          intel = _hydrateIntelFromMongo(userId, mongoDoc);
          saveIntel(userId, intel); // repopulate the local cache
          console.log(`[GET /level] Restored XP=${intel.xp} for user ${userId} from MongoDB`);
        }
      } catch (syncErr) {
        // Never fail the request because of a recovery error
        console.error("[GET /level] MongoDB recovery failed:", syncErr.message);
      }
    }

    const today      = todayStr();
    const levelInfo  = computeLevel(intel.xp || 0);
    const streak     = intel.streak?.days || 0;
    const todayEntry = (intel.dailySessions || []).find((s) => s.date === today);

    res.json({
      success: true,
      level: {
        currentLevel:       levelInfo.currentLevel,
        levelName:          levelInfo.levelName,
        xp:                 levelInfo.xpProgress,
        xpToNextLevel:      levelInfo.xpToNextLevel,
        totalXp:            intel.xp || 0,
        factsRead:          intel.factsRead || 0,
        mythsBusted:        intel.mythsBusted || 0,
        streak,
        achievements:       intel.achievements || [],
        categoriesExplored: intel.categoriesExplored || [],
        totalQuizCorrect:   intel.totalQuizCorrect || 0,
        totalQuizAnswered:  intel.totalQuizAnswered || 0,
        todaySession: todayEntry
          ? {
              date:             todayEntry.date,
              isCompleted:      todayEntry.isCompleted,
              xpEarned:         todayEntry.xpEarned,
              factsRead:        todayEntry.factsRead,
              quizScore:        todayEntry.quizScore,
              quizTotal:        todayEntry.quizTotal,
              completedPackIds: todayEntry.completedPackIds,
            }
          : null,
      },
    });
  } catch (error) {
    console.error("Get level error:", error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// POST /level  — award XP after a session, detect level-up
// ─────────────────────────────────────────────────────────────────────────────
router.post("/level", auth, async (req, res) => {
  try {
    const userId = req.userId;
    const {
      xpEarned  = 0,
      factsRead = 0,
      quizScore = 0,
      quizTotal = 0,
      packId,
    } = req.body;
    const today = todayStr();

    const intel     = getOrCreateIntel(userId);
    const prevXp    = intel.xp || 0;
    const prevLevel = computeLevel(prevXp).currentLevel;

    intel.xp              = prevXp + xpEarned;
    intel.factsRead       = (intel.factsRead       || 0) + factsRead;
    intel.totalQuizCorrect  = (intel.totalQuizCorrect  || 0) + quizScore;
    intel.totalQuizAnswered = (intel.totalQuizAnswered || 0) + quizTotal;

    if (!intel.dailySessions) intel.dailySessions = [];
    const sessionIdx = intel.dailySessions.findIndex((s) => s.date === today);
    if (sessionIdx >= 0) {
      const s = intel.dailySessions[sessionIdx];
      s.factsRead   = (s.factsRead   || 0) + factsRead;
      s.quizScore   = (s.quizScore   || 0) + quizScore;
      s.quizTotal   = (s.quizTotal   || 0) + quizTotal;
      s.xpEarned    = (s.xpEarned    || 0) + xpEarned;
      s.isCompleted = s.factsRead >= 3;
      if (packId && !(s.completedPackIds || []).includes(packId)) {
        s.completedPackIds = [...(s.completedPackIds || []), packId];
      }
    } else {
      intel.dailySessions.push({
        date:             today,
        factsRead,
        quizScore,
        quizTotal,
        xpEarned,
        isCompleted:      factsRead >= 3,
        completedPackIds: packId ? [packId] : [],
      });
    }

    // Streak logic
    if (!intel.streak) intel.streak = { days: 0, lastDate: null, longest: 0 };
    const lastDate  = intel.streak.lastDate;
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const yStr = yesterday.toISOString().split("T")[0];

    if (lastDate === today) {
      // already counted today
    } else if (lastDate === yStr) {
      intel.streak.days    = (intel.streak.days || 0) + 1;
      intel.streak.lastDate = today;
    } else {
      intel.streak.days    = 1;
      intel.streak.lastDate = today;
    }
    intel.streak.longest = Math.max(intel.streak.longest || 0, intel.streak.days);

    // Achievements
    if (!intel.achievements) intel.achievements = [];
    const earned = [];
    const checkAchievement = (type, badge, title, condition) => {
      if (condition && !intel.achievements.find((a) => a.type === type)) {
        const a = { type, badge, title, unlockedAt: new Date().toISOString() };
        intel.achievements.push(a);
        earned.push(a);
      }
    };

    checkAchievement("first_fact",   "🌱", "First Fact!",     intel.factsRead >= 1);
    checkAchievement("10_facts",     "📚", "10 Facts Read",   intel.factsRead >= 10);
    checkAchievement("50_facts",     "🧠", "50 Facts Read",   intel.factsRead >= 50);
    checkAchievement("quiz_perfect", "🎯", "Perfect Quiz",    quizScore > 0 && quizScore === quizTotal && quizTotal >= 3);
    checkAchievement("streak_3",     "🔥", "3-Day Streak",    intel.streak.days >= 3);
    checkAchievement("streak_7",     "🏆", "7-Day Streak",    intel.streak.days >= 7);
    checkAchievement("level_3",      "⭐", "Level 3 Reached", computeLevel(intel.xp).currentLevel >= 3);
    checkAchievement("level_5",      "💎", "Level 5 Reached", computeLevel(intel.xp).currentLevel >= 5);

    saveIntel(userId, intel);

    const newLevelInfo = computeLevel(intel.xp);
    const leveledUp    = newLevelInfo.currentLevel > prevLevel;

    // ── Sync absolute values into MongoDB so admin panel shows live data ──
    // FIX 1: new mongoose.Types.ObjectId(userId) — req.userId is a plain
    //   string but the schema field is ObjectId. Without the cast the query
    //   never matches and upsert silently creates a duplicate string-keyed doc.
    // FIX 2: $set with ABSOLUTE values (not $inc) so the data stays in sync
    //   with jsonStore and retries never double-count.
    try {
      await UserIntelligence.findOneAndUpdate(
        { userId: new mongoose.Types.ObjectId(userId) },
        {
          $set: {
            xp:                 intel.xp,
            factsRead:          intel.factsRead          || 0,
            mythsBusted:        intel.mythsBusted         || 0,
            totalQuizCorrect:   intel.totalQuizCorrect    || 0,
            totalQuizAnswered:  intel.totalQuizAnswered   || 0,
            level:              newLevelInfo.currentLevel,
            "streak.days":      intel.streak.days         || 0,
            "streak.lastDate":  intel.streak.lastDate     || null,
            "streak.longest":   intel.streak.longest      || 0,
            achievements:       intel.achievements        || [],
            dailySessions:      intel.dailySessions       || [],
            categoriesExplored: intel.categoriesExplored  || [],
          },
        },
        { upsert: true, new: false }
      );
    } catch (syncErr) {
      // Never fail the user request because of a MongoDB sync error
      console.error("[factsLearning] MongoDB sync error:", syncErr.message);
    }

    res.json({
      success:         true,
      xpEarned,
      totalXp:         intel.xp,
      level:           newLevelInfo.currentLevel,
      levelName:       newLevelInfo.levelName,
      xpProgress:      newLevelInfo.xpProgress,
      xpToNextLevel:   newLevelInfo.xpToNextLevel,
      leveledUp,
      streak:          intel.streak.days,
      newAchievements: earned,
    });
  } catch (error) {
    console.error("Post level error:", error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// POST /read  — mark a single fact read, award XP
// ─────────────────────────────────────────────────────────────────────────────
router.post("/read", auth, async (req, res) => {
  try {
    const { category } = req.body;
    const userId       = req.userId;

    const intel    = getOrCreateIntel(userId);
    const streak   = intel.streak?.days || 0;
    const xpBonus  = streak >= 3 ? XP_STREAK_BONUS : 0;
    const xpAward  = XP_PER_FACT + xpBonus;

    intel.xp        = (intel.xp        || 0) + xpAward;
    intel.factsRead = (intel.factsRead || 0) + 1;

    if (category) {
      if (!intel.categoriesExplored) intel.categoriesExplored = [];
      const existing = intel.categoriesExplored.find((c) => c.category === category);
      if (existing) {
        existing.factsRead    = (existing.factsRead || 0) + 1;
        existing.lastAccessed = new Date().toISOString();
      } else {
        intel.categoriesExplored.push({ category, factsRead: 1, lastAccessed: new Date().toISOString() });
      }
    }

    saveIntel(userId, intel);

    // ── PERSISTENCE FIX: sync XP to MongoDB on every fact read so data
    //    survives server restarts / ephemeral filesystems. ──────────────────
    try {
      const levelInfo = computeLevel(intel.xp);
      await UserIntelligence.findOneAndUpdate(
        { userId: new mongoose.Types.ObjectId(userId) },
        {
          $set: {
            xp:                 intel.xp,
            factsRead:          intel.factsRead          || 0,
            level:              levelInfo.currentLevel,
            categoriesExplored: intel.categoriesExplored || [],
            "streak.days":      intel.streak?.days       || 0,
            "streak.lastDate":  intel.streak?.lastDate   || null,
            "streak.longest":   intel.streak?.longest    || 0,
          },
        },
        { upsert: true, new: false }
      );
    } catch (syncErr) {
      console.error("[POST /read] MongoDB sync error:", syncErr.message);
    }

    const levelInfo = computeLevel(intel.xp);
    res.json({
      success:       true,
      xpEarned:      xpAward,
      totalXp:       intel.xp,
      level:         levelInfo.currentLevel,
      levelName:     levelInfo.levelName,
      xpProgress:    levelInfo.xpProgress,
      xpToNextLevel: levelInfo.xpToNextLevel,
      streak:        intel.streak?.days || 0,
    });
  } catch (error) {
    console.error("Mark read error:", error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// POST /quiz/submit
// ─────────────────────────────────────────────────────────────────────────────
router.post("/quiz/submit", auth, (req, res) => {
  try {
    const { answers = [], packId } = req.body;
    const userId  = req.userId;
    const correct = answers.filter((a) => a.selectedOptionId === a.correctOptionId).length;
    const total   = answers.length;
    const xpEarned = correct * XP_PER_QUIZ_RIGHT;

    const intel = getOrCreateIntel(userId);
    intel.xp              = (intel.xp              || 0) + xpEarned;
    intel.totalQuizCorrect  = (intel.totalQuizCorrect  || 0) + correct;
    intel.totalQuizAnswered = (intel.totalQuizAnswered || 0) + total;

    const mythAnswers = answers.filter((a) => a.isMythBuster);
    if (mythAnswers.length > 0) {
      intel.mythsBusted =
        (intel.mythsBusted || 0) +
        mythAnswers.filter((a) => a.selectedOptionId === a.correctOptionId).length;
    }

    saveIntel(userId, intel);

    const levelInfo = computeLevel(intel.xp);
    res.json({
      success:       true,
      correct,
      total,
      xpEarned,
      totalXp:       intel.xp,
      level:         levelInfo.currentLevel,
      levelName:     levelInfo.levelName,
      xpProgress:    levelInfo.xpProgress,
      xpToNextLevel: levelInfo.xpToNextLevel,
      accuracy:      total > 0 ? Math.round((correct / total) * 100) : 0,
    });
  } catch (error) {
    console.error("Quiz submit error:", error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// GET /myth-busters
// ─────────────────────────────────────────────────────────────────────────────
router.get("/myth-busters", auth, (req, res) => {
  try {
    const knowledge = readKnowledge();
    const myths = [];

    for (const entry of knowledge) {
      for (const fact of entry.facts || []) {
        if (fact.isMythBuster) {
          myths.push({
            factId:        fact._id,
            category:      fact.category || "Myth Busters",
            mythStatement: fact.mythStatement || fact.title,
            isTruth:       fact.isTruth,
            explanation:   fact.description,
            fullDetail:    fact.fullDetail,
            emoji:         fact.emoji || "❓",
            accentColor:   fact.accentColor,
            cardColor:     fact.cardColor,
            level:         entry.level,
          });
        }
      }
    }

    shuffle(myths);
    res.json({ success: true, myths });
  } catch (error) {
    console.error("Myth busters error:", error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// POST /myth-busters/answer
// ─────────────────────────────────────────────────────────────────────────────
router.post("/myth-busters/answer", auth, (req, res) => {
  try {
    const { factId, answer } = req.body;
    const userId = req.userId;

    const knowledge = readKnowledge();
    let foundFact = null;
    for (const entry of knowledge) {
      const f = (entry.facts || []).find((x) => x._id === factId);
      if (f) { foundFact = f; break; }
    }
    if (!foundFact) return res.status(404).json({ success: false, error: "Fact not found" });

    const correct  = String(foundFact.isTruth) === String(answer === "true");
    const intel    = getOrCreateIntel(userId);
    const xpEarned = correct ? XP_PER_QUIZ_RIGHT : 0;

    intel.xp              = (intel.xp              || 0) + xpEarned;
    intel.mythsBusted     = (intel.mythsBusted     || 0) + (correct ? 1 : 0);
    intel.totalQuizCorrect  = (intel.totalQuizCorrect  || 0) + (correct ? 1 : 0);
    intel.totalQuizAnswered = (intel.totalQuizAnswered || 0) + 1;

    saveIntel(userId, intel);

    res.json({
      success:     true,
      correct,
      isTruth:     foundFact.isTruth,
      explanation: foundFact.description,
      xpEarned,
      totalXp:     intel.xp,
    });
  } catch (error) {
    console.error("Myth answer error:", error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// GET /by-level  (legacy — redirects to facts-for-level logic)
// ─────────────────────────────────────────────────────────────────────────────
router.get("/by-level", auth, (req, res) => {
  try {
    const userId = req.userId;
    const intel  = getOrCreateIntel(userId);
    const { currentLevel } = computeLevel(intel.xp || 0);
    const knowledge = readKnowledge();
    const cfg       = getLevelConfig(currentLevel);

    let entry = getLevelEntry(knowledge, currentLevel);
    if (!entry) {
      const candidates = knowledge.filter((e) => e.level <= currentLevel);
      entry = candidates.length ? candidates[candidates.length - 1] : knowledge[0];
    }

    const facts = (entry.facts || []).map((f) => enrichFact(f, f.category || ""));
    shuffle(facts);
    res.json({ success: true, facts: facts.slice(0, cfg.factsTarget), level: currentLevel });
  } catch (error) {
    console.error("By level error:", error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// GET /random
// ─────────────────────────────────────────────────────────────────────────────
router.get("/random", auth, (req, res) => {
  try {
    const knowledge = readKnowledge();
    const all = [];
    for (const entry of knowledge) {
      for (const f of entry.facts || []) all.push(enrichFact(f, f.category || ""));
    }
    if (all.length === 0)
      return res.status(404).json({ success: false, error: "No facts found" });
    const random = all[Math.floor(Math.random() * all.length)];
    res.json({ success: true, fact: random });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// GET /daily-session
// ─────────────────────────────────────────────────────────────────────────────
router.get("/daily-session", auth, (req, res) => {
  try {
    const userId  = req.userId;
    const intel   = getOrCreateIntel(userId);
    const today   = todayStr();
    const session = (intel.dailySessions || []).find((s) => s.date === today) || null;
    res.json({ success: true, session });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// GET /packs
// ─────────────────────────────────────────────────────────────────────────────
router.get("/packs", auth, (req, res) => {
  try {
    const userId = req.userId;
    const intel  = getOrCreateIntel(userId);
    const { currentLevel } = computeLevel(intel.xp || 0);

    const PACK_DEFINITIONS = [
      { id: "hair_growth",    title: "Hair Growth Science", emoji: "🧬", requiredLevel: 1, accentColor: "#4ECDC4", cardColor: "#001A18" },
      { id: "scalp_biology",  title: "Scalp Biology",       emoji: "🔬", requiredLevel: 2, accentColor: "#00B4D8", cardColor: "#001520" },
      { id: "nutrition",      title: "Nutrition & Hair",    emoji: "🥗", requiredLevel: 3, accentColor: "#00E676", cardColor: "#001A0A" },
      { id: "myth_busters",   title: "Myth Busters",        emoji: "💥", requiredLevel: 4, accentColor: "#FF6B9D", cardColor: "#1A0010" },
      { id: "hair_loss",      title: "Hair Loss Causes",    emoji: "🔍", requiredLevel: 5, accentColor: "#FF8C42", cardColor: "#1A0800" },
      { id: "medical_truths", title: "Medical Truths",      emoji: "🏥", requiredLevel: 6, accentColor: "#9B30FF", cardColor: "#0F0020" },
      { id: "trichology_pro", title: "Trichology Pro",      emoji: "🎓", requiredLevel: 7, accentColor: "#FFD166", cardColor: "#1A1200" },
    ];

    // Count facts per level from new knowledge structure
    const knowledge = readKnowledge();
    const countByLevel = {};
    for (const entry of knowledge) {
      countByLevel[entry.level] = (entry.facts || []).length;
    }

    const completedPacks = new Set(
      (intel.dailySessions || []).flatMap((s) => s.completedPackIds || [])
    );

    const packs = PACK_DEFINITIONS.map((def) => ({
      ...def,
      isUnlocked:     currentLevel >= def.requiredLevel,
      isCompleted:    completedPacks.has(def.id),
      totalFacts:     countByLevel[def.requiredLevel] || 0,
      completedFacts: completedPacks.has(def.id) ? countByLevel[def.requiredLevel] || 0 : 0,
    }));

    res.json({ success: true, packs, userLevel: currentLevel });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// POST /packs/:packId/complete
// ─────────────────────────────────────────────────────────────────────────────
router.post("/packs/:packId/complete", auth, (req, res) => {
  try {
    const { packId } = req.params;
    const userId     = req.userId;
    const today      = todayStr();

    const intel = getOrCreateIntel(userId);
    if (!intel.dailySessions) intel.dailySessions = [];

    const sessionIdx = intel.dailySessions.findIndex((s) => s.date === today);
    if (sessionIdx >= 0) {
      const s = intel.dailySessions[sessionIdx];
      if (!s.completedPackIds) s.completedPackIds = [];
      if (!s.completedPackIds.includes(packId)) s.completedPackIds.push(packId);
    } else {
      intel.dailySessions.push({
        date:             today,
        isCompleted:      false,
        completedPackIds: [packId],
        factsRead:        0,
        quizScore:        0,
        quizTotal:        0,
        xpEarned:         0,
      });
    }

    saveIntel(userId, intel);
    res.json({ success: true, packId });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

module.exports = router;
// ─────────────────────────────────────────────────────────────────────────────
// POST /go-to-previous-level
// Sets XP to the floor of (currentLevel - 1) so the user replays the previous
// level from scratch. Returns the new level info so Flutter can update state
// immediately without a second round-trip to GET /level.
// Level 1 → returns early with alreadyAtMin: true.
// ─────────────────────────────────────────────────────────────────────────────
router.post("/go-to-previous-level", auth, async (req, res) => {
  try {
    const userId           = req.userId;
    const intel            = getOrCreateIntel(userId);
    const { currentLevel } = computeLevel(intel.xp || 0);

    if (currentLevel <= 1) {
      const info = computeLevel(intel.xp || 0);
      return res.json({
        success:       true,
        alreadyAtMin:  true,
        level:         info.currentLevel,
        levelName:     info.levelName,
        xpProgress:    info.xpProgress,
        xpToNextLevel: info.xpToNextLevel,
        totalXp:       intel.xp || 0,
      });
    }

    // XP floor = xpRequired of (currentLevel - 1)
    const prevEntry = LEVELS.find((l) => l.level === currentLevel - 1);
    const targetXp  = prevEntry ? prevEntry.xpRequired : 0;

    intel.xp               = targetXp;
    intel.totalQuizCorrect  = 0;
    intel.totalQuizAnswered = 0;
    saveIntel(userId, intel);

    // Sync to MongoDB (non-blocking)
    try {
      await UserIntelligence.findOneAndUpdate(
        { userId: new mongoose.Types.ObjectId(userId) },
        { $set: { xp: targetXp, level: currentLevel - 1, totalQuizCorrect: 0, totalQuizAnswered: 0 } },
        { upsert: false }
      );
    } catch (syncErr) {
      console.error("[go-to-previous-level] MongoDB sync error:", syncErr.message);
    }

    const newInfo = computeLevel(targetXp);
    res.json({
      success:       true,
      level:         newInfo.currentLevel,
      levelName:     newInfo.levelName,
      xpProgress:    newInfo.xpProgress,
      xpToNextLevel: newInfo.xpToNextLevel,
      totalXp:       targetXp,
    });
  } catch (error) {
    console.error("go-to-previous-level error:", error);
    res.status(500).json({ success: false, error: error.message });
  }
});