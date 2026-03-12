const AiResult = require("../models/AIResult");
const { callAnalyze } = require("./flask.service");

function extractS3Key(url) {
  if (!url) return null;
  return url.split(".amazonaws.com/")[1];
}

function normalizeHairloss(hl) {
  if (!hl) return {};
  const views = hl.views || {};
  const normalizeView = (v) => {
    if (!v) return {};
    return {
      severity: v.severity ?? "unknown",
      damage:   v.damage   ?? null,
      weight:   v.weight   ?? null,
    };
  };
  return {
    overallSeverity: hl.overallSeverity ?? hl.overall_severity ?? "unknown",
    combinedDamage:  hl.combinedDamage  ?? hl.combined_damage  ?? null,
    overlayImageKey: hl.overlayImageKey ?? hl.overlay_image_key ?? null,
    views: {
      top:   normalizeView(views.top),
      front: normalizeView(views.front),
      back:  normalizeView(views.back),
    },
    summary: hl.summary ?? null,
  };
}

function normalizeRootCause(rc) {
  if (!rc || Object.keys(rc).length === 0) return {};
  return {
    primary:   rc.primary   ?? rc.primaryCause   ?? null,
    secondary: rc.secondary ?? rc.secondaryCause ?? null,
    details:   rc.details   ?? rc.nodes          ?? rc,
  };
}

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
        top:   extractS3Key(reqBody.topImageUrl),
        front: extractS3Key(reqBody.frontImageUrl),
        back:  extractS3Key(reqBody.backImageUrl),
      },
      hairloss: normalizeHairloss(flaskResponse.hairloss),
      dandruff: flaskResponse.dandruff || {},
      health: flaskResponse.health || {},

      lifestyle: flaskResponse.lifestyle || {},

      rootCause: normalizeRootCause(flaskResponse.rootCause),

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