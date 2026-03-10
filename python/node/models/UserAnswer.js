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
      index: true,
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

module.exports = mongoose.model("UserAnswer", UserAnswerSchema);