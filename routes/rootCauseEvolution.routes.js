const express = require("express");
const router = express.Router();
const UserIntelligence = require("../models/UserIntelligence");
const auth = require("../middleware/auth");

router.post("/save", auth, async (req, res) => {
  try {
    const { causes, overallTrend, changes } = req.body;
    const userId = req.user.id;

    let userIntel = await UserIntelligence.findOne({ userId });
    if (!userIntel) {
      userIntel = await UserIntelligence.create({ userId });
    }

    userIntel.rootCauseHistory.push({
      date: new Date(),
      causes,
      overallTrend,
      changes,
    });

    await userIntel.save();

    res.json({
      success: true,
      historyCount: userIntel.rootCauseHistory.length,
    });

  } catch (error) {
    console.error("Save root cause error:", error);
    res.status(500).json({ success: false, error: error.message });
  }
});

module.exports = router;