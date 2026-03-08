const AiResult = require("../models/AIResult");
const { callAnalyze } = require("./flask.service");

exports.triggerAIAnalysis = async (reqBody) => {
  try {
    const flaskResponse = await callAnalyze(reqBody);

    if (!flaskResponse.success) {
      throw new Error(flaskResponse.error || "AI failed");
    }

    const aiResult = await AiResult.create({
      userId: reqBody.userId,

      status: "completed",

      images: {
        top: reqBody.topImageUrl || "",
        front: reqBody.frontImageUrl || "",
        back: reqBody.backImageUrl || "",
      },

      hairloss: flaskResponse.hairloss || {},
      dandruff: flaskResponse.dandruff || {},
      health: flaskResponse.health || {},

      lifestyle: flaskResponse.lifestyle || {},

      rootCause: flaskResponse.rootCause || {},

      suggestions: flaskResponse.suggestions || {},
      tipsAndRemedies: flaskResponse.tipsAndRemedies || {},

      futureRisk: flaskResponse.futureRisk || {},
      timeline: flaskResponse.timeline || {},

      simulation: flaskResponse.simulation || {},
      adaptiveRoutine: flaskResponse.adaptiveRoutine || {},

      progress: flaskResponse.progress || {},

      assistantContext: flaskResponse.assistantContext || {},

      aiResponse: flaskResponse,
    });

    return aiResult;
  } catch (error) {

    if (error.response?.data) {
      throw new Error(
        error.response.data.error ||
        error.response.data.message ||
        "AI processing failed"
      );
    }

    throw new Error("Unable to connect to AI service");
  }
};