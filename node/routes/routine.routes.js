const express = require("express");
const router = express.Router();
const axios = require("axios");
const authMiddleware = require("../middleware/auth");
const UserIntelligence = require("../models/UserIntelligence");
const AIResult = require("../models/AIResult");
const notifService = require("../services/notifications.service");

router.use(authMiddleware);

const PYTHON_AI_URL = process.env.PYTHON_AI_URL || "http://127.0.0.1:5001";

/* ─────────────────────────────────────────────
   Helpers
─────────────────────────────────────────────── */

function todayStr() {
  return new Date().toISOString().split("T")[0];
}

function yesterdayStr() {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toISOString().split("T")[0];
}

function getTaskEmoji(title = "", category = "") {
  const t = title.toLowerCase();
  if (t.includes("massage") || t.includes("scalp")) return "💆";
  if (t.includes("shampoo"))                         return "🧴";
  if (t.includes("oil"))                             return "🫙";
  if (t.includes("comb") || t.includes("braid"))    return "💇";
  if (t.includes("water") || t.includes("hydrat"))  return "💧";
  if (t.includes("sleep"))                           return "😴";
  if (t.includes("vitamin") || t.includes("supplement")) return "💊";
  if (t.includes("protein") || t.includes("snack") || t.includes("breakfast")) return "🌅";
  if (t.includes("dinner") || t.includes("iron"))   return "🌙";
  if (category === "morning")                        return "🌅";
  if (category === "night")                          return "🌙";
  return "✅";
}

const DEFAULT_TASKS = [
  { title: "Detangle gently with wide-tooth comb", category: "morning", emoji: "💇", xp: 10, completed: false },
  { title: "5 min scalp massage",                  category: "night",   emoji: "💆", xp: 15, completed: false },
  { title: "Loose braid before sleep",             category: "night",   emoji: "🌙", xp: 10, completed: false },
];

/* ─────────────────────────────────────────────
   Task generator
─────────────────────────────────────────────── */

async function generateTasksFromAI(aiReport) {
  let tasks = [];
  try {
    const py = await axios.post(
      `${PYTHON_AI_URL}/adaptive-routine`,
      {
        hairlossSeverity: aiReport?.hairloss?.overallSeverity || "moderate",
        dandruffSeverity: aiReport?.dandruff?.severity        || "moderate",
        rootCause:        aiReport?.rootCause?.primary        || "general",
      },
      { timeout: 8000 },
    );

    const routineData = py.data?.routine || py.data || {};
    Object.entries(routineData).forEach(([slot, items]) => {
      if (!Array.isArray(items)) return;
      items.forEach((t) => {
        const title = t.task || t.title || "Task";
        tasks.push({
          title,
          category:    slot === "mid_day" ? "daily" : slot,
          emoji:       getTaskEmoji(title, slot),
          xp:          t.xp || 10,
          completed:   false,
          completedAt: null,
        });
      });
    });
  } catch (err) {
    console.log("Python routine failed, using fallback tasks");
  }
  return tasks.length ? tasks : DEFAULT_TASKS;
}

/* ═══════════════════════════════════════════════
   GET /api/routine
═══════════════════════════════════════════════ */

router.get("/", async (req, res) => {
  try {
    const userId = req.userId;
    const today  = todayStr();

    // ── Check if user has a completed AI report ───────────────
    const latestAI = await AIResult.findOne({ userId, status: "completed" })
      .sort({ createdAt: -1 })
      .lean();

    if (!latestAI) {
      return res.json({
        success:   true,
        hasReport: false,
        routine:   { tasks: [] },
        xp:        0,
        level:     1,
        streakDays:     0,
        longestStreak:  0,
        completedDates: [],
      });
    }

    // ── Get or create UserIntelligence ────────────────────────
    let userIntel = await UserIntelligence.findOne({ userId });
    if (!userIntel) {
      userIntel = await UserIntelligence.create({ userId, xp: 0, level: 1 });
    }

    if (!Array.isArray(userIntel.routines))       userIntel.routines       = [];
    if (!Array.isArray(userIntel.completedDates)) userIntel.completedDates = [];

    // ── Get or build today's routine ──────────────────────────
    let routine = userIntel.routines.find((r) => r.date === today);
    if (!routine) {
      const tasks = await generateTasksFromAI(latestAI);
      routine = { date: today, tasks, totalXP: 0, allDone: false };
      userIntel.routines.push(routine);
      await userIntel.save();
      // Re-fetch to get the embedded doc reference
      routine = userIntel.routines.find((r) => r.date === today);
    }

    const completedCount = routine.tasks.filter((t) => t.completed).length;

    res.json({
      success:        true,
      hasReport:      true,
      routine,
      xp:             userIntel.xp     || 0,
      level:          userIntel.level  || 1,
      completedCount,
      // ✅ Return streak data so the UI calendar works immediately
      streakDays:     userIntel.streak?.days    || 0,
      longestStreak:  userIntel.streak?.longest || 0,
      completedDates: userIntel.completedDates  || [],
    });
  } catch (err) {
    console.error("Routine GET error", err);
    res.status(500).json({ success: false, error: err.message });
  }
});

/* ═══════════════════════════════════════════════
   POST /api/routine/complete
═══════════════════════════════════════════════ */

router.post("/complete", async (req, res) => {
  try {
    let { date, taskIndex } = req.body;
    const userId = req.userId;

    // Normalise date
    date = date
      ? new Date(date).toISOString().split("T")[0]
      : todayStr();

    const today     = todayStr();

    // ── Load user intel ───────────────────────────────────────
    let userIntel = await UserIntelligence.findOne({ userId });
    if (!userIntel) {
      return res.status(404).json({ success: false, error: "User intelligence not found" });
    }

    if (!Array.isArray(userIntel.routines))       userIntel.routines       = [];
    if (!Array.isArray(userIntel.completedDates)) userIntel.completedDates = [];

    // Ensure streak sub-doc exists
    if (!userIntel.streak) {
      userIntel.streak = { days: 0, lastDate: null, longest: 0 };
    }

    // ── Find today's routine (regenerate if missing) ──────────
    let routine = userIntel.routines.find((r) => r.date === date);
    if (!routine) {
      const latestAI = await AIResult.findOne({ userId, status: "completed" })
        .sort({ createdAt: -1 })
        .lean();
      const tasks = await generateTasksFromAI(latestAI);
      routine = { date, tasks, totalXP: 0, allDone: false };
      userIntel.routines.push(routine);
      routine = userIntel.routines[userIntel.routines.length - 1];
    }

    // ── Validate task index ───────────────────────────────────
    const index = Number(taskIndex);
    if (!Array.isArray(routine.tasks) || index < 0 || index >= routine.tasks.length) {
      return res.status(400).json({ success: false, error: "Invalid task index" });
    }

    const task = routine.tasks[index];

    // ── Mark task complete (idempotent) ───────────────────────
    if (!task.completed) {
      task.completed   = true;
      task.completedAt = new Date();

      const xp = task.xp || 10;
      routine.totalXP        = (routine.totalXP || 0) + xp;
      userIntel.xp           = (userIntel.xp    || 0) + xp;

      notifService.add(
        userId.toString(),
        `⚡ +${xp} XP — "${task.title}" completed!`,
        "routine",
      );
    }

    // ── Check if ALL tasks are now done ───────────────────────
    routine.allDone = routine.tasks.every((t) => t.completed);

    // ── Update streak when the full day is completed ────────────
    // FIX: guard was `!completedDates.includes(date)` — if the date had been
    // added previously (race or retry), streak.days was never incremented,
    // causing "1 day done but 0 streak" shown in the screenshot.
    // Now: always add date to completedDates (idempotent set), then recompute
    // streak.days by walking the sorted completedDates, so the value is always
    // correct regardless of how many times this route is called.
    if (routine.allDone) {

      // ── Idempotent insert ───────────────────────────────────
      if (!userIntel.completedDates.includes(date)) {
        userIntel.completedDates.push(date);
      }

      // ── Recompute current streak from completedDates ────────
      // Sort ascending, then walk backwards from today counting consecutive days.
      const sortedDates = [...new Set(userIntel.completedDates)].sort();
      let streak = 0;
      const todayDate = new Date(todayStr());

      // Walk from the most recent date backwards
      for (let i = sortedDates.length - 1; i >= 0; i--) {
        const d = new Date(sortedDates[i]);
        // Expected date = today - streak days
        const expected = new Date(todayDate);
        expected.setDate(expected.getDate() - streak);
        const expectedStr = expected.toISOString().split("T")[0];

        if (sortedDates[i] === expectedStr) {
          streak++;
        } else {
          break; // gap found — stop
        }
      }

      userIntel.streak.days = streak;

      // Update longest streak
      if (streak > (userIntel.streak.longest || 0)) {
        userIntel.streak.longest = streak;
      }

      // Update lastDate to the most recent completedDate
      userIntel.streak.lastDate = sortedDates[sortedDates.length - 1];

      notifService.add(
        userId.toString(),
        `🔥 ${streak}-day streak! All routines complete for ${date}!`,
        "streak",
      );
    }

    // Mongoose doesn't detect nested array mutations automatically
    userIntel.markModified("routines");
    userIntel.markModified("streak");
    userIntel.markModified("completedDates");

    await userIntel.save();

    res.json({
      success:        true,
      xp:             userIntel.xp,
      level:          userIntel.level || 1,
      totalXP:        routine.totalXP,
      allDone:        routine.allDone,
      // ✅ Return correct field names that Flutter reads
      streak:         userIntel.streak.days,
      longestStreak:  userIntel.streak.longest,
      completedDates: userIntel.completedDates,
    });

  } catch (err) {
    console.error("[Routine Complete Error]", err);
    res.status(500).json({ success: false, error: err.message });
  }
});

/* ═══════════════════════════════════════════════
   POST /api/routine/reset
═══════════════════════════════════════════════ */

router.post("/reset", async (req, res) => {
  try {
    const userId = req.userId;
    const today  = todayStr();

    const userIntel = await UserIntelligence.findOne({ userId });
    if (!userIntel) {
      return res.status(404).json({ success: false, error: "Not found" });
    }

    const routine = userIntel.routines.find((r) => r.date === today);
    if (routine) {
      routine.tasks.forEach((t) => {
        t.completed   = false;
        t.completedAt = null;
      });
      routine.totalXP = 0;
      routine.allDone = false;

      userIntel.markModified("routines");
      await userIntel.save();
    }

    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

/* ═══════════════════════════════════════════════
   POST /api/streak/restart
═══════════════════════════════════════════════ */

router.post("/streak/restart", async (req, res) => {
  try {
    const userId    = req.userId;
    const today     = todayStr();
    const userIntel = await UserIntelligence.findOne({ userId });

    if (!userIntel) {
      return res.status(404).json({ success: false, error: "Not found" });
    }

    // ── Reset streak counter, keep longest streak history ──────
    const prevLongest = userIntel.streak?.longest || 0;
    userIntel.streak = { days: 0, lastDate: null, longest: prevLongest };

    // ── Reset today's routine tasks and deduct XP ────────────
    // FIX: original code reset tasks but never subtracted the earned XP,
    // so the user kept the points even after restarting.
    const routine = userIntel.routines.find((r) => r.date === today);
    if (routine) {
      // Deduct the XP that was earned today from the user's total
      const xpToDeduct = routine.totalXP || 0;
      userIntel.xp = Math.max(0, (userIntel.xp || 0) - xpToDeduct);

      routine.tasks.forEach((t) => { t.completed = false; t.completedAt = null; });
      routine.totalXP = 0;
      routine.allDone = false;
    }

    // ── Remove today from completedDates ─────────────────────
    userIntel.completedDates = (userIntel.completedDates || []).filter(
      (d) => d !== today
    );

    userIntel.markModified("routines");
    userIntel.markModified("streak");
    userIntel.markModified("completedDates");

    await userIntel.save();

    res.json({
      success:        true,
      streak:         0,
      longestStreak:  prevLongest,
      xp:             userIntel.xp,
      completedDates: userIntel.completedDates,
    });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

module.exports = router;