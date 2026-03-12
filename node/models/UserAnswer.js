const mongoose = require("mongoose");

const AnswerSchema = new mongoose.Schema({
  cardId: { type: String, required: true },
  question: { type: String, required: true },
  selectedAnswer: {
    type: [String],
    required: true,
  },
});

const UserAnswerSchema = new mongoose.Schema(
  {
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
      // NOTE: unique index is defined below at schema level (not here)
      // to avoid the stale "username_1" index conflict
    },

    attemptNumber: {
      type: Number,
      default: 1,
    },

    answers: {
      type: [AnswerSchema],
      default: [],
    },
  },
  { timestamps: true }
);

// Explicit unique index on userId only — one answers doc per user
UserAnswerSchema.index({ userId: 1 }, { unique: true });

// ── Drop stale indexes on first load ──────────────────────────────────────────
// The old collection had a "username_1" unique index (from a previous schema).
// This hook removes it automatically so new users can submit answers.
UserAnswerSchema.post("init", function () {});

async function dropStaleIndexes(model) {
  try {
    const indexes = await model.collection.indexes();
    for (const idx of indexes) {
      if (idx.name === "username_1") {
        await model.collection.dropIndex("username_1");
        console.log("[UserAnswer] Dropped stale index: username_1");
      }
    }
  } catch (e) {
    // Index may not exist on fresh deployments — safe to ignore
    if (e.code !== 27) {
      console.warn("[UserAnswer] dropStaleIndexes warning:", e.message);
    }
  }
}

const UserAnswer = mongoose.model("UserAnswer", UserAnswerSchema);

// Drop stale index after connection is ready
mongoose.connection.once("open", () => dropStaleIndexes(UserAnswer));

module.exports = UserAnswer;