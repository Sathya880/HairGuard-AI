const mongoose = require("mongoose");

/* =====================================================
   🔹 VIEW SEVERITY SCHEMA
===================================================== */

const ViewSeveritySchema = new mongoose.Schema(
  {
    severity: {
      type: String,
      enum: [
        "none",
        "low",
        "mild",
        "moderate",
        "high",
        "severe",
        "very_severe",
        "unknown",
      ],
      default: "unknown",
    },
    damage: {
      type: Number,
      min: 0,
      max: 100,
    },
    weight: {
      type: Number,
      min: 0,
      max: 1,
    },
  },
  { _id: false },
);

/* =====================================================
   🔹 MAIN AI RESULT SCHEMA
===================================================== */

const AIResultSchema = new mongoose.Schema(
  {
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
      index: true,
    },

    type: {
      type: String,
      enum: ["hair_analysis"],
      default: "hair_analysis",
    },

    status: {
      type: String,
      enum: ["processing", "completed", "failed"],
      default: "processing",
      required: true,
      index: true,
    },

    /* IMAGES */

    images: {
      top: { type: String, required: true },
      front: String,
      back: String,
    },
    /* HAIRLOSS */

    hairloss: {
      overallSeverity: {
        type: String,
        enum: [
          "none",
          "low",
          "mild",
          "moderate",
          "high",
          "severe",
          "very_severe",
          "unknown",
        ],
        default: "unknown",
      },

      combinedDamage: { type: Number, min: 0, max: 100 },

      overlayImageUrl: String, // only top overlay

      views: {
        top: { type: ViewSeveritySchema, default: {} },
        front: { type: ViewSeveritySchema, default: {} },
        back: { type: ViewSeveritySchema, default: {} },
      },
      summary: String,
    },

    /* DANDRUFF */

    dandruff: {
      severity: {
        type: String,
        enum: ["none", "low", "mild", "moderate", "severe", "unknown"],
        default: "unknown",
      },

      overlayImageUrl: String,
      summary: String,
    },

    /* HEALTH */

    health: {
      score: { type: Number, min: 0, max: 100 },
      label: String,
      breakdown: mongoose.Schema.Types.Mixed,
    },

    /* LIFESTYLE */

    lifestyle: mongoose.Schema.Types.Mixed,

    /* ROOT CAUSE */

    rootCause: {
      primary: String,
      secondary: String,
      details: mongoose.Schema.Types.Mixed,
    },

    /* OUTPUT */

    suggestions: mongoose.Schema.Types.Mixed,
    tipsAndRemedies: mongoose.Schema.Types.Mixed,
    futureRisk: mongoose.Schema.Types.Mixed,
    timeline: mongoose.Schema.Types.Mixed,

    /* PROGRESS */

    progress: {
      previousScore: Number,
      currentScore: Number,
      scoreChange: Number,

      hairTrend: {
        type: String,
        enum: ["Improved", "Worsened", "Stable", "First Scan"],
      },

      dandruffTrend: {
        type: String,
        enum: ["Improved", "Worsened", "Stable", "First Scan"],
      },
    },

    /* SIMULATION */

    simulation: mongoose.Schema.Types.Mixed,

    adaptiveRoutine: mongoose.Schema.Types.Mixed,

    /* ASSISTANT */

    assistantContext: mongoose.Schema.Types.Mixed,

    assistant: {
      state: String,
      message: String,
      tone: String,
      suggestions: mongoose.Schema.Types.Mixed,
    },

    /* DEBUG */

    engineVersion: String,
    modelVersion: String,

    aiResponse: {
      type: mongoose.Schema.Types.Mixed,
      select: false,
    },

    error: String,
  },
  {
    timestamps: true,
    strict: true,
  },
);

/* INDEXES */

AIResultSchema.index({ userId: 1, createdAt: -1 });
AIResultSchema.index({ userId: 1, status: 1 });

AIResultSchema.index(
  { userId: 1 },
  {
    unique: true,
    partialFilterExpression: { status: "processing" },
  },
);

AIResultSchema.index(
  { createdAt: 1 },
  { expireAfterSeconds: 86400, partialFilterExpression: { status: "failed" } }
);

module.exports =
  mongoose.models.AIResult || mongoose.model("AIResult", AIResultSchema);
