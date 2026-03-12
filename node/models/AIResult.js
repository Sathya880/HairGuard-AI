const mongoose = require("mongoose");

/* =====================================================
   VIEW SEVERITY SCHEMA
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
      default: null,
    },

    weight: {
      type: Number,
      min: 0,
      max: 1,
      default: null,
    },
  },
  { _id: false }
);

/* =====================================================
   PROGRESS SCHEMA
===================================================== */

const ProgressSchema = new mongoose.Schema(
  {
    previousScore: {
      type: Number,
      default: null,
    },

    currentScore: {
      type: Number,
      default: null,
    },

    scoreChange: {
      type: Number,
      default: null,
    },

    hairTrend: {
      type: String,
      enum: ["Improved", "Worsened", "Stable", "First Scan"],
      default: "First Scan",
    },

    dandruffTrend: {
      type: String,
      enum: ["Improved", "Worsened", "Stable", "First Scan"],
      default: "First Scan",
    },
  },
  { _id: false }
);

/* =====================================================
   MAIN AI RESULT SCHEMA
===================================================== */

const AIResultSchema = new mongoose.Schema(
  {
    /* USER */

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
      index: true,
    },

    /* INPUT IMAGES */

    images: {
      top: {
        type: String,
        required: true,
      },

      front: {
        type: String,
        default: null,
      },

      back: {
        type: String,
        default: null,
      },
    },

    /* HAIR LOSS ANALYSIS */

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

      combinedDamage: {
        type: Number,
        min: 0,
        max: 100,
        default: null,
      },

      overlayImageKey: {
        type: String,
        default: null,
      },

      views: {
        top: { type: ViewSeveritySchema, default: () => ({}) },
        front: { type: ViewSeveritySchema, default: () => ({}) },
        back: { type: ViewSeveritySchema, default: () => ({}) },
      },

      summary: {
        type: String,
        default: null,
      },
    },

    /* DANDRUFF */

    dandruff: {
      severity: {
        type: String,
        enum: ["none", "low", "mild", "moderate", "severe", "unknown"],
        default: "unknown",
      },

      overlayImageKey: {
        type: String,
        default: null,
      },

      summary: {
        type: String,
        default: null,
      },
    },

    /* HAIR HEALTH */

    health: {
      score: {
        type: Number,
        min: 0,
        max: 100,
        default: null,
      },

      label: {
        type: String,
        default: null,
      },

      breakdown: {
        type: mongoose.Schema.Types.Mixed,
        default: {},
      },
    },

    /* LIFESTYLE */

    lifestyle: {
      type: mongoose.Schema.Types.Mixed,
      default: {},
    },

    /* ROOT CAUSE */

    rootCause: {
      primary: { type: String, default: null },
      secondary: { type: String, default: null },
      details: { type: mongoose.Schema.Types.Mixed, default: {} },
    },

    /* RECOMMENDATIONS */

    suggestions: {
      type: mongoose.Schema.Types.Mixed,
      default: {},
    },

    tipsAndRemedies: {
      type: mongoose.Schema.Types.Mixed,
      default: {},
    },

    futureRisk: {
      type: mongoose.Schema.Types.Mixed,
      default: {},
    },

    timeline: {
      type: mongoose.Schema.Types.Mixed,
      default: {},
    },

    /* PROGRESS */

    progress: {
      type: ProgressSchema,
      default: () => ({}),
    },

    /* SIMULATION */

    simulation: {
      type: mongoose.Schema.Types.Mixed,
      default: {},
    },

    adaptiveRoutine: {
      type: mongoose.Schema.Types.Mixed,
      default: {},
    },

    /* ASSISTANT */

    assistantContext: {
      type: mongoose.Schema.Types.Mixed,
      default: {},
    },

    assistant: {
      state: { type: String, default: null },
      message: { type: String, default: null },
      tone: { type: String, default: null },
      suggestions: { type: mongoose.Schema.Types.Mixed, default: {} },
    },

    /* DEBUG */

    engineVersion: { type: String, default: null },
    modelVersion: { type: String, default: null },

    aiResponse: {
      type: mongoose.Schema.Types.Mixed,
      select: false,
    },

    error: {
      type: String,
      default: null,
    },
  },
  {
    timestamps: true,
    strict: true,
  }
);

/* =====================================================
   INDEXES
===================================================== */

AIResultSchema.index({ userId: 1, createdAt: -1 });

AIResultSchema.index({ userId: 1, status: 1 });

AIResultSchema.index(
  { userId: 1 },
  {
    unique: true,
    partialFilterExpression: { status: "processing" },
  }
);

AIResultSchema.index(
  { createdAt: 1 },
  {
    expireAfterSeconds: 86400,
    partialFilterExpression: { status: "failed" },
  }
);

module.exports =
  mongoose.models.AIResult ||
  mongoose.model("AIResult", AIResultSchema);