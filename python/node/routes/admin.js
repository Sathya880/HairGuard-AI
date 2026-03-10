/**
 * ============================================================
 *  HAIRAI ADMIN ROUTES  —  routes/admin.js
 *  Mount this in your Express app:
 *    const adminRouter = require('./routes/admin');
 *    app.use('/api/admin', adminRouter);
 * ============================================================
 */

const express    = require("express");
const router     = express.Router();
const User       = require("../models/User");
const AIResult   = require("../models/AIResult");
const UserAnswer = require("../models/UserAnswer");
const ChatHistory   = require("../models/ChatHistory");
const UserIntelligence = require("../models/UserIntelligence");

// ── Admin credentials from env (with safe defaults for dev) ──────────────────
const ADMIN_USERNAME = process.env.ADMIN_USERNAME || "admin";
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || "admin@123";
// Simple shared secret — in production replace with a signed JWT
const ADMIN_SESSION_TOKEN = process.env.ADMIN_SESSION_TOKEN || "local_admin_session";

// ── Auth middleware ───────────────────────────────────────────────────────────
const adminAuth = (req, res, next) => {
  const authHeader = req.headers.authorization || "";
  const token = authHeader.startsWith("Bearer ")
    ? authHeader.slice(7).trim()
    : authHeader.trim();

  if (token && token === ADMIN_SESSION_TOKEN) {
    return next();
  }
  return res.status(401).json({ success: false, message: "Unauthorized" });
};

// ── LOGIN ─────────────────────────────────────────────────────────────────────
router.post("/login", (req, res) => {
  const { username, password } = req.body || {};
  if (
    username === ADMIN_USERNAME &&
    password === ADMIN_PASSWORD
  ) {
    return res.json({ success: true, token: ADMIN_SESSION_TOKEN });
  }
  return res.status(401).json({ success: false, message: "Invalid credentials" });
});

// Apply auth middleware to every route defined after this line
router.use(adminAuth);

// ── DASHBOARD STATS ───────────────────────────────────────────────────────────
router.get("/stats", async (req, res) => {
  try {
    const [totalUsers, completedAnalyses, processingAnalyses] = await Promise.all([
      User.countDocuments(),
      AIResult.countDocuments({ status: "completed" }),
      AIResult.countDocuments({ status: "processing" }),
    ]);

    const monthAgo = new Date();
    monthAgo.setMonth(monthAgo.getMonth() - 1);
    const newUsersThisMonth = await User.countDocuments({
      createdAt: { $gte: monthAgo },
    });

    // "Active today" = users who have any AI result updated today
    const todayStart = new Date();
    todayStart.setHours(0, 0, 0, 0);
    const activeTodayIds = await AIResult.distinct("userId", {
      updatedAt: { $gte: todayStart },
    });

    // Hairloss severity distribution
    const hairlossDist = await AIResult.aggregate([
      { $match: { status: "completed" } },
      { $group: { _id: "$hairloss.overallSeverity", count: { $sum: 1 } } },
    ]);
    const severityDistribution = {};
    hairlossDist.forEach(d => {
      severityDistribution[d._id || "unknown"] = d.count;
    });

    // Dandruff distribution
    const dandruffDist = await AIResult.aggregate([
      { $match: { status: "completed" } },
      { $group: { _id: "$dandruff.severity", count: { $sum: 1 } } },
    ]);
    const dandruffDistribution = {};
    dandruffDist.forEach(d => {
      dandruffDistribution[d._id || "unknown"] = d.count;
    });

    // Avg health score
    const healthAgg = await AIResult.aggregate([
      { $match: { status: "completed", "health.score": { $exists: true, $ne: null } } },
      { $group: { _id: null, avg: { $avg: "$health.score" } } },
    ]);
    const avgHealthScore = healthAgg.length ? Math.round(healthAgg[0].avg) : 0;

    return res.json({
      totalUsers,
      newUsersThisMonth,
      totalAnalyses: completedAnalyses + processingAnalyses,
      completedAnalyses,
      activeToday: activeTodayIds.length,
      avgHealthScore,
      severityDistribution,
      dandruffDistribution,
    });
  } catch (err) {
    console.error("Admin /stats error:", err);
    return res.status(500).json({ error: err.message });
  }
});

// ── ALL USERS ─────────────────────────────────────────────────────────────────
router.get("/users", async (req, res) => {
  try {
    const users = await User.find()
      .select("-hash -salt")   // exclude passport-local fields
      .sort({ createdAt: -1 })
      .lean();
    res.json({ users });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── SINGLE USER ───────────────────────────────────────────────────────────────
router.get("/users/:userId", async (req, res) => {
  try {
    const user = await User.findById(req.params.userId)
      .select("-hash -salt")
      .lean();
    if (!user) return res.status(404).json({ error: "User not found" });
    res.json(user);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── USER AI RESULTS ───────────────────────────────────────────────────────────
router.get("/users/:userId/ai-results", async (req, res) => {
  try {
    const results = await AIResult.find({ userId: req.params.userId })
      .sort({ createdAt: -1 })
      .lean();
    res.json({ results });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── USER ANSWERS ──────────────────────────────────────────────────────────────
router.get("/users/:userId/answers", async (req, res) => {
  try {
    const answers = await UserAnswer.find({ userId: req.params.userId })
      .sort({ createdAt: -1 })
      .lean();
    res.json({ answers });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── USER INTELLIGENCE (Routines + Facts + XP) ─────────────────────────────────
router.get("/users/:userId/intelligence", async (req, res) => {
  try {
    const intel = await UserIntelligence.findOne({ userId: req.params.userId }).lean();
    // Return empty object (not 404) so the Flutter client can render gracefully
    res.json(intel ?? {});
  } catch (err) {
    console.error("Admin /intelligence error:", err);
    res.status(500).json({ error: err.message });
  }
});

// ── CHAT HISTORY ──────────────────────────────────────────────────────────────
router.get("/users/:userId/chat", async (req, res) => {
  try {
    const chat = await ChatHistory.findOne({ userId: req.params.userId }).lean();
    res.json({ messages: chat?.messages ?? [] });
  } catch (err) {
    console.error("Admin /chat error:", err);
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;