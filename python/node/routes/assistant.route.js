const express = require("express");
const router = express.Router();
const OpenAI = require("openai");

const ChatHistory = require("../models/ChatHistory");
const AIResult = require("../models/AIResult");

const authMiddleware = require("../middleware/auth");

/* =====================================================
   HUGGINGFACE MODEL CLIENT
===================================================== */

// Models tried in order when one is unavailable (503 / 5xx)
const HF_MODELS = [
  "moonshotai/Kimi-K2-Instruct",
  "Qwen/Qwen2.5-72B-Instruct",
  "meta-llama/Llama-3.3-70B-Instruct",
  "mistralai/Mistral-7B-Instruct-v0.3",
];

let hf = null;

if (process.env.HF_TOKEN) {
  hf = new OpenAI({
    baseURL: "https://router.huggingface.co/v1",
    apiKey: process.env.HF_TOKEN,
  });
  console.log("[Assistant] ✅ HuggingFace AI ready");
} else {
  console.warn("[Assistant] ⚠️ HF_TOKEN not set");
}

/* =====================================================
   HELPER — safe userId
===================================================== */

function getUserId(req) {
  return req.user?._id ?? req.user?.id ?? null;
}


function getLifestyleScore(report) {
  return (
    report?.lifestyle?.overallScore ??
    report?.lifestyle?.overall_score ??
    report?.lifestyle?.overall ??
    report?.lifestyle?.score ??
    report?.lifestyle?.totalScore ??
    report?.lifestyleScore ??
    50
  );
}

/* =====================================================
   SYSTEM PROMPT
===================================================== */

function buildSystemPrompt(report) {
  const hairScore = report?.health?.score ?? 50;
  const lifestyleScore = getLifestyleScore(report);

  const hairSev =
    report?.hairloss?.overallSeverity ?? report?.hairSeverity ?? "unknown";
  const dandruffSev =
    report?.dandruff?.severity ?? report?.dandruffSeverity ?? "unknown";
  const rootCause = report?.rootCause?.primary ?? "unknown";

  return `You are an expert AI Hair Health Coach.

User report:
Hair Score: ${hairScore}/100
Hair Loss: ${hairSev}
Dandruff: ${dandruffSev}
Root Cause: ${rootCause}
Lifestyle Score: ${lifestyleScore}/100

Rules:
- Use the user's actual numbers
- Simple, friendly language
- Under 200 words
- Use bullet points where helpful
- End with ONE clear next step`;
}

/* =====================================================
   AI REPLY — tries each HF model in order
===================================================== */

async function getAIReply(actionType, userMessage, report) {
  if (!hf) return "AI service not configured. Please set HF_TOKEN.";

  let prompt = userMessage;

  if (actionType === "explain") {
    prompt = `Explain my hair health report in simple, easy-to-understand language.

Hair Score: ${report?.health?.score ?? "N/A"}/100
Hair Loss Severity: ${report?.hairloss?.overallSeverity ?? "N/A"}
Dandruff Severity: ${report?.dandruff?.severity ?? "N/A"}
Root Cause: ${report?.rootCause?.primary ?? "N/A"}
Lifestyle Score: ${getLifestyleScore(report)}/100

Please explain what each number means for my hair health.`;
  }

  if (actionType === "improve") {
    prompt = `Create a personalised hair improvement plan for me.

My current hair score is ${report?.health?.score ?? "N/A"}/100.
Primary root cause: ${report?.rootCause?.primary ?? "N/A"}
Hair loss severity: ${report?.hairloss?.overallSeverity ?? "N/A"}
Lifestyle score: ${report?.lifestyle?.overallScore ?? report?.lifestyle?.score ?? "N/A"}/100

Give me a step-by-step improvement plan with realistic timelines.`;
  }

  const systemPrompt = buildSystemPrompt(report);
  let lastError = null;

  for (const model of HF_MODELS) {
    try {
      const completion = await hf.chat.completions.create({
        model,
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: prompt },
        ],
        temperature: 0.5,
        max_tokens: 500,
      });

      const reply = completion?.choices?.[0]?.message?.content;
      if (reply) {
        console.log(`[Assistant] ✅ Reply from model: ${model}`);
        return reply;
      }
    } catch (err) {
      const status = err?.status ?? err?.response?.status;
      console.warn(`[Assistant] ⚠️ Model ${model} failed (${status}): ${err.message}`);
      lastError = err;

      // Only try fallback on server-side errors (5xx) or rate limit (429)
      if (status && status < 400) break;
    }
  }

  console.error("[Assistant] All HF models failed:", lastError?.message);
  return "I'm having trouble connecting to the AI service right now. Please try again in a few moments.";
}

/* =====================================================
   ROUTE: POST /ask
   Actions: explain | improve | qa
===================================================== */

router.post("/ask", authMiddleware, async (req, res) => {
  try {
    const userId = getUserId(req);
    if (!userId) {
      return res.status(401).json({ success: false, message: "Authentication error" });
    }

    const { message = "", actionType = "qa" } = req.body;

    const latestAI = await AIResult.findOne({ userId, status: "completed" })
      .sort({ createdAt: -1 })
      .lean();

    if (!latestAI) {
      return res.status(400).json({
        success: false,
        message: "Please run a hair analysis first before using the AI coach.",
      });
    }

    const reply = await getAIReply(actionType, message, latestAI);

    // Save to chat history (best-effort — don't fail the request if this errors)
    try {
      await ChatHistory.findOneAndUpdate(
        { userId },
        {
          $setOnInsert: { userId },
          $push: {
            messages: {
              $each: [
                { role: "user", content: message || actionType, timestamp: new Date() },
                { role: "assistant", content: reply, timestamp: new Date() },
              ],
            },
          },
        },
        { upsert: true }
      );
    } catch (histErr) {
      console.warn("[Assistant] Chat history save failed:", histErr.message);
    }

    res.json({ success: true, reply });
  } catch (err) {
    console.error("[Assistant] /ask error:", err);
    res.status(500).json({ success: false, message: "AI service error" });
  }
});

/* =====================================================
   ROUTE: POST /simulate
   Body: { factors: { reduceStress, improveSleep, ... } }
   Returns: { baseScore, predictedScore, totalBoost,
              recoveryTimeline, narrative, improvements[] }
===================================================== */

router.post("/simulate", authMiddleware, async (req, res) => {
  try {
    const userId = getUserId(req);
    if (!userId) {
      return res.status(401).json({ success: false, message: "Authentication error" });
    }

    const { factors = {} } = req.body;

    // ── 1. Get user's latest report for base values ──────────────────────────
    const latestAI = await AIResult.findOne({ userId, status: "completed" })
      .sort({ createdAt: -1 })
      .lean();

    const baseScore = latestAI?.health?.score ?? 50;
    const hairlossSeverity = latestAI?.hairloss?.overallSeverity ?? "moderate";
    const dandruffSeverity = latestAI?.dandruff?.severity ?? "moderate";
    const lifestyleScore =
      latestAI?.lifestyle?.overallScore ?? latestAI?.lifestyle?.score ?? 50;

    // ── 2. Map Flutter factor keys → SimulationEngine improvement keys ───────
    const improvements = {
      stress_reduced:      !!factors.reduceStress,
      sleep_improved:      !!factors.improveSleep,
      scalp_care_improved: !!factors.controlDandruff,
      hydration_improved:  !!factors.improveHydration,
      diet_improved:       !!factors.improveDiet,
      hair_care_improved:  !!factors.improveRoutine,
    };

    // ── 3. Call Python SimulationEngine ──────────────────────────────────────
    const FLASK_URL = process.env.FLASK_URL || "https://hairguard-ai.onrender.com";
    let simResult = null;

    try {
      const flaskRes = await fetch(`${FLASK_URL}/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          currentHairScore: baseScore,
          lifestyleScore,
          improvements,
          hairlossSeverity,
          dandruffSeverity,
        }),
        signal: AbortSignal.timeout(10000),
      });

      const flaskData = await flaskRes.json();
      if (flaskData.success) simResult = flaskData.simulation;
    } catch (flaskErr) {
      console.warn("[Simulate] Flask call failed, using local fallback:", flaskErr.message);
    }

    // ── 4. Local fallback if Flask is unavailable ────────────────────────────
    if (!simResult) {
      simResult = _localSimulate(baseScore, improvements, hairlossSeverity);
    }

    // ── 5. Build Flutter-friendly response ────────────────────────────────────
    const predictedScore = Math.min(
      100,
      Math.round(simResult.projected_hair_score ?? baseScore)
    );
    const totalBoost = Math.max(0, predictedScore - baseScore);

    const FACTOR_META = {
      reduceStress:     { label: "Reduce Stress",        tip: "10-min daily walks and limit screen time before bed",       weight: 18 },
      improveSleep:     { label: "Improve Sleep",         tip: "Aim for 7–8 hours of uninterrupted sleep nightly",          weight: 15 },
      controlDandruff:  { label: "Control Dandruff",      tip: "Use ketoconazole or zinc pyrithione shampoo 2–3× per week", weight: 12 },
      improveHydration: { label: "Better Hydration",      tip: "Drink 2–3 litres of water daily",                           weight: 10 },
      improveDiet:      { label: "Improve Diet",          tip: "Add lean protein, biotin, zinc, and omega-3 to your meals",  weight: 20 },
      improveRoutine:   { label: "Follow Hair Routine",   tip: "Consistent daily scalp care and product application",       weight: 12 },
    };

    const activeFactors = Object.entries(factors).filter(([, v]) => v);
    const totalWeight = activeFactors.reduce(
      (sum, [k]) => sum + (FACTOR_META[k]?.weight ?? 10),
      0
    );

    const improvementsList = activeFactors.map(([key]) => {
      const meta = FACTOR_META[key] ?? { label: key, tip: "", weight: 10 };
      const pts = totalWeight > 0
        ? Math.round((meta.weight / totalWeight) * totalBoost)
        : 0;
      return { factor: meta.label, points: pts, tip: meta.tip };
    });

    // Recovery timeline
    const timelineMap = {
      1: "6–8 weeks", 2: "5–7 weeks", 3: "4–6 weeks",
      4: "3–5 weeks", 5: "3–4 weeks", 6: "2–4 weeks",
    };
    const recoveryTimeline = timelineMap[activeFactors.length] ?? "4–8 weeks";

    // Narrative
    const confidence = simResult.confidence_level ?? "Moderate";
    const narrative = totalBoost > 0
      ? `By implementing ${activeFactors.length} change${activeFactors.length !== 1 ? "s" : ""}, ` +
        `your hair score could rise from ${baseScore} to ${predictedScore} within ${recoveryTimeline}. ` +
        `${confidence} confidence based on your current profile.`
      : `Select at least one lifestyle change to see projected improvements for your hair score of ${baseScore}/100.`;

    res.json({
      success: true,
      simulation: {
        baseScore,
        predictedScore,
        totalBoost,
        recoveryTimeline,
        narrative,
        improvements: improvementsList,
        confidence,
      },
    });
  } catch (err) {
    console.error("[Simulate] Error:", err);
    res.status(500).json({ success: false, message: "Simulation error" });
  }
});

/* =====================================================
   LOCAL SIMULATION FALLBACK
   Mirrors Python SimulationEngine logic
===================================================== */

function _localSimulate(baseScore, improvements, hairlossSeverity) {
  const weights = {
    stress_reduced:      18.0,
    diet_improved:       20.0,
    sleep_improved:      15.0,
    hair_care_improved:  12.0,
    scalp_care_improved: 15.0,
    hydration_improved:  10.0,
  };

  const interactions = [
    ["sleep_improved",      "stress_reduced",      0.20],
    ["diet_improved",       "hydration_improved",  0.15],
    ["scalp_care_improved", "hair_care_improved",  0.12],
  ];

  const severityMult = {
    none: 0.05, low: 0.07, mild: 0.10, moderate: 0.12,
    high: 0.15, severe: 0.18, very_severe: 0.20,
  };

  const active = Object.entries(improvements)
    .filter(([, v]) => v)
    .map(([k]) => k);

  let base = active.reduce((s, k) => s + (weights[k] ?? 0), 0);

  let bonus = 0;
  for (const [a, b, mult] of interactions) {
    if (active.includes(a) && active.includes(b)) bonus += base * mult;
  }

  const mult = severityMult[(hairlossSeverity ?? "moderate").toLowerCase()] ?? 0.10;
  const reduction = Math.min(45, Math.max(0, (base + bonus) * mult));

  const n = active.length;
  const confidence = n >= 5 ? "High" : n >= 3 ? "Moderate" : "Low";
  const weeks = n >= 5 ? 8 : n >= 3 ? 6 : n >= 1 ? 4 : 0;

  return {
    projected_hair_score: baseScore + reduction,
    projected_hair_fall_reduction_percent: reduction,
    confidence_level: confidence,
    timeline_weeks: weeks,
    factors_analyzed: active,
  };
}

/* =====================================================
   ROUTE: GET /history
===================================================== */

router.get("/history", authMiddleware, async (req, res) => {
  try {
    const userId = getUserId(req);
    const chat = await ChatHistory.findOne({ userId }).lean();
    res.json({ success: true, messages: chat?.messages?.slice(-50) ?? [] });
  } catch (err) {
    res.status(500).json({ success: false, message: "Error fetching history" });
  }
});

/* =====================================================
   ROUTE: POST /chat  (behavioral coaching from Python)
===================================================== */

router.post("/chat", authMiddleware, async (req, res) => {
  try {
    const { callAssistant } = require("../services/flask.service");
    const data = req.body;
    const result = await callAssistant(data);
    res.json({ success: true, assistant: result });
  } catch (err) {
    console.error("[Assistant] /chat error:", err);
    res.status(500).json({ success: false, message: "Assistant error" });
  }
});

module.exports = router;