const mongoose = require("mongoose");

// ─── Achievement sub-schema ───────────────────────────────────────────────────
const achievementSchema = new mongoose.Schema(
  {
    type: { type: String, required: true },
    badge: { type: String, default: "🏆" },
    title: { type: String, default: "" },
    description: { type: String, default: "" },
    unlockedAt: { type: Date, default: Date.now },
  },
  { _id: false }
);

// ─── Category progress sub-schema ────────────────────────────────────────────
const categoryProgressSchema = new mongoose.Schema(
  {
    category: { type: String, required: true },
    factsRead: { type: Number, default: 0 },
    lastAccessed: { type: Date, default: Date.now },
  },
  { _id: false }
);

// ─── Daily session sub-schema ─────────────────────────────────────────────────
const dailySessionSchema = new mongoose.Schema(
  {
    date: { type: String, required: true }, // "YYYY-MM-DD"
    isCompleted: { type: Boolean, default: false },
    xpEarned: { type: Number, default: 0 },
    factsRead: { type: Number, default: 0 },
    quizScore: { type: Number, default: 0 },
    quizTotal: { type: Number, default: 0 },
    completedPackIds: { type: [String], default: [] },
  },
  { _id: false }
);

// ─── Task sub-schema ──────────────────────────────────────────────────────────
const taskSchema = new mongoose.Schema(
  {
    title:       { type: String, default: "Task" },
    category:    { type: String, default: "daily" },
    emoji:       { type: String, default: "✅" },
    xp:          { type: Number, default: 10 },
    completed:   { type: Boolean, default: false },
    completedAt: { type: Date, default: null },
  },
  { _id: false }
);

// ─── Routine sub-schema ───────────────────────────────────────────────────────
const routineSchema = new mongoose.Schema(
  {
    date:           { type: String, required: true }, // "YYYY-MM-DD"
    tasks:          { type: [taskSchema], default: [] },
    totalXP:        { type: Number, default: 0 },
    allDone:        { type: Boolean, default: false },
    adherenceScore: { type: Number, default: 0 },
  },
  { _id: false }
);

// ─── Streak sub-schema ────────────────────────────────────────────────────────
// FIX: field name unified to "lastDate" (was mixed "lastDate"/"lastActiveDate")
const streakSchema = new mongoose.Schema(
  {
    days:     { type: Number, default: 0 },
    lastDate: { type: String, default: null },   // "YYYY-MM-DD"
    longest:  { type: Number, default: 0 },
  },
  { _id: false }
);

// ─── Main schema ──────────────────────────────────────────────────────────────
const userIntelligenceSchema = new mongoose.Schema(
  {
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
      unique: true,
      index: true,
    },

    xp:                { type: Number, default: 0 },
    level:             { type: Number, default: 1 },
    factsRead:         { type: Number, default: 0 },
    mythsBusted:       { type: Number, default: 0 },
    totalQuizCorrect:  { type: Number, default: 0 },
    totalQuizAnswered: { type: Number, default: 0 },

    streak: { type: streakSchema, default: () => ({}) },

    // ✅ FIX: completedDates was missing from schema — streak calendar needs this
    completedDates: { type: [String], default: [] },  // ["YYYY-MM-DD", ...]

    routines:           { type: [routineSchema],          default: [] },
    achievements:       { type: [achievementSchema],      default: [] },
    categoriesExplored: { type: [categoryProgressSchema], default: [] },
    dailySessions:      { type: [dailySessionSchema],     default: [] },
  },
  { timestamps: true }
);

module.exports = mongoose.model("UserIntelligence", userIntelligenceSchema);