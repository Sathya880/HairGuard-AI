/**
 * models/ChatHistory.js
 * Stores per-user chat messages for the AI Hair Coach assistant.
 */
const mongoose = require("mongoose");

const messageSchema = new mongoose.Schema(
  {
    role: {
      type: String,
      enum: ["user", "assistant"],
      required: true,
    },
    content: {
      type: String,
      required: true,
    },
    timestamp: {
      type: Date,
      default: Date.now,
    },
  },
  { _id: false }
);

const chatHistorySchema = new mongoose.Schema(
  {
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
      unique: true,
      index: true,
    },
    messages: {
      type: [messageSchema],
      default: [],
    },
  },
  { timestamps: true }
);

// Keep only the latest 200 messages per user to avoid unbounded growth
chatHistorySchema.pre("save", function (next) {
  if (this.messages.length > 200) {
    this.messages = this.messages.slice(-200);
  }
  next();
});

module.exports =
  mongoose.models.ChatHistory ||
  mongoose.model("ChatHistory", chatHistorySchema);