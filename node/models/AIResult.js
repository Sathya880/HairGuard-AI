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
      required: true,
      index: true,
    },

    /* INPUT IMAGES (S3 KEYS) */

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
      },

      /* S3 KEY of overlay */

      overlayImageKey: {
        type: String,
        default: null,
      },

      views: {
        top: {
          type: ViewSeveritySchema,
          default: {},
        },

        front: {
          type: ViewSeveritySchema,
          default: {},
        },

        back: {
          type: ViewSeveritySchema,
          default: {},
        },
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

      overlayImageKey: {
        type: String,
        default: null,
      },

      summary: String,
    },

    /* HAIR HEALTH */

    health: {
      score: {
        type: Number,
        min: 0,
        max: 100,
      },

      label: String,

      breakdown: mongoose.Schema.Types.Mixed,
    },

    /* LIFESTYLE ANALYSIS */

    lifestyle: mongoose.Schema.Types.Mixed,

    /* ROOT CAUSE */

    rootCause: {
      primary: String,
      secondary: String,
      details: mongoose.Schema.Types.Mixed,
    },

    /* RECOMMENDATIONS */

    suggestions: mongoose.Schema.Types.Mixed,

    tipsAndRemedies: mongoose.Schema.Types.Mixed,

    futureRisk: mongoose.Schema.Types.Mixed,

    timeline: mongoose.Schema.Types.Mixed,

    /* PROGRESS TRACKING */

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

    /* AI ASSISTANT CONTEXT */

    assistantContext: mongoose.Schema.Types.Mixed,

    assistant: {
      state: String,
      message: String,
      tone: String,
      suggestions: mongoose.Schema.Types.Mixed,
    },

    /* DEBUG / INTERNAL */

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
  }
);

/* =====================================================
   INDEXES
===================================================== */

/* Query user scan history */

AIResultSchema.index({ userId: 1, createdAt: -1 });

/* Find active analysis */

AIResultSchema.index({ userId: 1, status: 1 });

/* Prevent concurrent scans */

AIResultSchema.index(
  { userId: 1 },
  {
    unique: true,
    partialFilterExpression: { status: "processing" },
  }
);

/* Auto-delete failed scans after 24h */

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