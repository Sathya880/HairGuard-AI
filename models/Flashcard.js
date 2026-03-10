const mongoose = require("mongoose");

const flashcardSchema = new mongoose.Schema(
  {
    question: {
      type: String,
      required: true,
      trim: true,
    },

    options: {
      type: [String],
      required: true,
      set: opts => opts.map(o => o.trim()),
      validate: {
        validator: v => Array.isArray(v) && v.length >= 2,
        message: "A flashcard must have at least 2 options",
      },
    },

    category: {
      type: String,
      default: "General",
      index: true,
      trim: true,
    },

    factor: {
      type: String,
      enum: [
        "hair_wash",
        "shampoo_type",
        "heat_styling",
        "family_history",
        "stress",
        "helmet_usage",
        "diet",
        "sleep",
        "water_type",
        "problem_duration",
        "scalp_sweat"
      ],
      default: "default",
      index: true,
    },

    animationKey: {
      type: String,
      default: "default",
      trim: true,
    },
  },
  { timestamps: true }
);

module.exports = mongoose.model("Flashcard", flashcardSchema);