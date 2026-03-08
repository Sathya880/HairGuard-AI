const mongoose = require("mongoose");

// ─── Evidence sub-schema ─────────────────────────────────────
const evidenceSchema = new mongoose.Schema({
  evidenceLevel: {
    type: String,
    enum: [
      "Scientifically Proven",
      "Clinically Observed",
      "Traditional/Anecdotal",
      "Risky",
    ],
  },

  confidenceScore: {
    type: Number,
    min: 0,
    max: 100,
    default: 0,
  },

  sources: [
    {
      name: String,
      url: String,
      year: Number,
    },
  ],

  warnings: [
    {
      type: {
        type: String,
        enum: ["allergy", "interaction", "side-effect", "inappropriate-usage"],
      },
      description: String,
    },
  ],

  severity: {
    type: String,
    enum: ["low", "moderate", "high"],
    default: "low",
  },
});

// ─── Quiz option sub-schema ──────────────────────────────────
const quizOptionSchema = new mongoose.Schema(
  {
    id: { type: String, required: true },
    text: { type: String, required: true },
  },
  { _id: false }
);

// ─── Fact sub-schema ─────────────────────────────────────────
const factSchema = new mongoose.Schema({
  title: { type: String, required: true },

  description: { type: String, required: true },

  fullDetail: { type: String, required: true },

  emoji: String,

  accentColor: String,

  cardColor: String,

  learningLevel: {
    type: Number,
    min: 1,
    max: 3,
    default: 1,
  },

  isMythBuster: { type: Boolean, default: false },

  mythStatement: String,

  isTruth: Boolean,

  severityLevel: {
    type: String,
    enum: ["low", "moderate", "high"],
    default: "moderate",
  },

  tags: [String],

  // ─── Quiz fields ─────────────────────────────
  quizOptions: [quizOptionSchema],

  correctAnswer: String,

  evidence: evidenceSchema,
});

// ─── Knowledge category schema ───────────────────────────────
const hairKnowledgeSystemSchema = new mongoose.Schema(
  {
    category: {
      type: String,
      enum: [
        "Hair Growth Science",
        "Scalp Biology",
        "Lifestyle Impact",
        "Myth Busters",
        "Medical Truths",
      ],
      index: true,
    },

    facts: [factSchema],

    isActive: {
      type: Boolean,
      default: true,
      index: true,
    },
  },
  { timestamps: true }
);

// ─── Indexes (must be after schema declaration) ──────────────
hairKnowledgeSystemSchema.index({ "facts._id": 1 });
hairKnowledgeSystemSchema.index({ category: 1 });

// ─── Model export ────────────────────────────────────────────
module.exports = mongoose.model(
  "HairKnowledgeSystem",
  hairKnowledgeSystemSchema
);