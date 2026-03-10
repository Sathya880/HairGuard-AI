const AiResult = require("./AIResult");

/**
 * Save lifestyle score into the user's latest AI analysis.
 * Priority:
 * 1. Active processing record
 * 2. Latest completed record
 */
async function saveLifestyleScore(userId, lifestyleData) {
  if (!userId) {
    console.warn("LifestyleScore: Missing userId");
    return null;
  }

  if (!lifestyleData || typeof lifestyleData !== "object") {
    console.warn("LifestyleScore: Invalid lifestyle data");
    return null;
  }

  try {
    // 1️⃣ Try updating active processing record first
    let updated = await AiResult.findOneAndUpdate(
      { userId, status: "processing" },
      { $set: { lifestyle: lifestyleData } },
      {
        new: true,
        runValidators: false,
      }
    );

    // 2️⃣ If no processing record, update latest completed
    if (!updated) {
      updated = await AiResult.findOneAndUpdate(
        { userId, status: "completed" },
        { $set: { lifestyle: lifestyleData } },
        {
          sort: { createdAt: -1 },
          new: true,
          runValidators: false,
        }
      );
    }

    if (!updated) {
      console.warn(
        "LifestyleScore: No AI analysis found to attach lifestyle data."
      );
      return null;
    }

    return updated;

  } catch (err) {
    console.error(
      "LifestyleScore save failed (non-critical):",
      err.message
    );
    return null;
  }
}

module.exports = saveLifestyleScore;