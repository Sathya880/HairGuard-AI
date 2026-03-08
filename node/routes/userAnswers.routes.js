const express = require("express");
const router = express.Router();
const UserAnswer = require("../models/UserAnswer");
const authenticateUser = require("../middleware/auth");

/**
 * POST /submit10
 * Save all flashcard answers — userId comes from JWT, NOT request body.
 */
router.post("/submit10", authenticateUser, async (req, res) => {
  try {
    const userId = req.user._id; // ✅ from JWT
    const { answers } = req.body;

    if (!Array.isArray(answers) || answers.length === 0) {
      return res.status(400).json({
        success: false,
        message: "answers array is required",
      });
    }

    // 🧹 Clean + validate each answer
    const cleanAnswers = answers
      .filter(
        (a) =>
          a &&
          a.cardId &&
          typeof a.question === "string" &&
          Array.isArray(a.selectedAnswer) &&
          a.selectedAnswer.length > 0
      )
      .map((a) => ({
        cardId: a.cardId.toString(),
        question: a.question.trim(),
        selectedAnswer: a.selectedAnswer.map((s) => String(s).trim()),
      }));

    if (cleanAnswers.length !== answers.length) {
      return res.status(400).json({
        success: false,
        message: "All answers must be valid (cardId, question, selectedAnswer required)",
      });
    }

    // 🔁 ONE DOCUMENT PER USER — upsert
    await UserAnswer.findOneAndUpdate(
      { userId },
      { userId, answers: cleanAnswers },
      { upsert: true, new: true, setDefaultsOnInsert: true }
    );

    return res.json({
      success: true,
      message: `${cleanAnswers.length} answers saved successfully`,
    });
  } catch (err) {
    console.error("Save answers error:", err);
    return res.status(500).json({
      success: false,
      message: err.message,
    });
  }
});

/**
 * GET /exists
 * Check if user has saved answers — userId from JWT, no query param needed.
 */
router.get("/exists", authenticateUser, async (req, res) => {
  try {
    const userId = req.user._id; // ✅ from JWT

    const doc = await UserAnswer.findOne({ userId }).lean();

    return res.json({
      success: true,
      exists: !!doc && Array.isArray(doc.answers) && doc.answers.length > 0,
    });
  } catch (err) {
    console.error("Check exists error:", err);
    return res.status(500).json({
      success: false,
      exists: false,
    });
  }
});

module.exports = router;