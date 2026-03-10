const express = require("express");
const mongoose = require("mongoose");
const passport = require("passport");
const session = require("express-session");
const LocalStrategy = require("passport-local").Strategy;
const cors = require("cors");
const helmet = require("helmet");
const axios = require("axios");

const { v4: uuidv4 } = require("uuid");
require("dotenv").config();

const pLimit = require("p-limit");
const aiLimiter = pLimit(2);


/* ── MODELS ──────────────────────────────────────── */
const User = require("./models/User");
const authenticateUser = require("./middleware/auth");
const Flashcard = require("./models/Flashcard");
const UserAnswer = require("./models/UserAnswer");
const AiResult = require("./models/AIResult");
const UserIntelligence = require("./models/UserIntelligence");

/* ── IN-APP NOTIFICATION SERVICE ─────────────────── */
const notifService = require("./services/notifications.service");

const app = express();

/* ── ENV ─────────────────────────────────────────── */
const PORT = process.env.PORT || 5000;
const SESSION_SECRET = process.env.SESSION_SECRET || "hair_app_secret";
const PYTHON_AI_URL =
  process.env.PYTHON_AI_URL || "https://sathyaj8-hairguard-ai.hf.space";

const connectDB = require("./config/db");
connectDB();

/* ── MIDDLEWARE ──────────────────────────────────── */
app.use(
  cors({
    origin: "*",
    methods: ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allowedHeaders: ["Content-Type", "Authorization"],
  }),
);
app.use(helmet());
app.use(express.json());
app.use(
  session({
    secret: SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
  }),
);

// ─────────────────────────────────────────────
// S3 PRESIGNED UPLOAD URL (SECURE)
// ─────────────────────────────────────────────

const AWS = require("aws-sdk");

const s3 = new AWS.S3({
  region: process.env.AWS_REGION,
  accessKeyId: process.env.AWS_ACCESS_KEY_ID,
  secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
});

const S3_BUCKET = process.env.AWS_BUCKET_NAME;

app.post("/api/upload/presign", authenticateUser, async (req, res) => {
  try {
    const { filename, contentType, username } = req.body;

    if (!filename || !contentType) {
      return res.status(400).json({
        success: false,
        message: "filename and contentType required",
      });
    }

    const uniqueId = uuidv4();

    const key = `hair/${username}/${uniqueId}_${filename}`;

    const params = {
      Bucket: S3_BUCKET,
      Key: key,
      Expires: 60,
      ContentType: contentType,
    };

    const uploadUrl = await s3.getSignedUrlPromise("putObject", params);

    return res.json({
      success: true,
      uploadUrl,
      key,
    });
  } catch (err) {
    console.error("Presign error:", err);

    return res.status(500).json({
      success: false,
      message: "Failed to generate upload URL",
    });
  }
});

/* ── PASSPORT ────────────────────────────────────── */
app.use(passport.initialize());
app.use(passport.session());
passport.use(new LocalStrategy(User.authenticate()));
passport.serializeUser(User.serializeUser());
passport.deserializeUser(User.deserializeUser());

const { debugPaths, readKnowledge } = require("./utils/jsonStore");

debugPaths();

// Quick sanity check — logs how many facts loaded on boot
const categories = readKnowledge();
const total = categories.reduce((acc, c) => acc + (c.facts?.length || 0), 0);
console.log(
  `[Startup] Hair Knowledge: ${categories.length} categories, ${total} facts loaded`,
);

if (total === 0) {
  console.error("⚠️  [Startup] ZERO facts loaded from hairKnowledge.json!");
  console.error("    → Check that the file exists at the path shown above.");
  console.error(
    "    → Check that it is a valid JSON array of category objects.",
  );
  console.error(
    "    → Each category must have isActive: true and a non-empty facts[] array.",
  );
}

/* ── AUTH ROUTES ─────────────────────────────────── */
app.get("/api/auth/me", authenticateUser, async (req, res) => {
  const user = await User.findById(req.user._id).select(
    "name username age gender",
  );
  res.json({ success: true, user });
});

const authRoutes = require("./routes/auth.routes");
app.use("/api/auth", authRoutes);
app.use("/api/user-answers", require("./routes/userAnswers.routes"));

// ── Routine & Streak routes ──────────────────────────────────────────────
const routineRoutes = require("./routes/routine.routes");
const chatbotRoute = require("./routes/chatbot");
app.use("/api/chatbot", chatbotRoute);

app.use("/api/routine", routineRoutes);
app.use("/api/streak", routineRoutes);

const adminRouter = require("./routes/admin");
app.use("/api/admin", adminRouter);

// ── Assistant routes (behavioral coaching + AI Hair Coach) ───────────────
const assistantRoute = require("./routes/assistant.route");
app.use("/api/assistant", assistantRoute);

// ── Facts Learning routes (Duolingo-style) ───────────────────────────────
const factsLearningRoutes = require("./routes/factsLearning.routes");
app.use("/api/facts-learning", factsLearningRoutes);

// ── Helper for AI analyze notification ───────────────────────────────────
function normalizeFactor(factor = "") {
  return factor
    .toString()
    .toLowerCase()
    .trim()
    .replace(/-/g, "_")
    .replace(/\s+/g, "_");
}

/* ── Per-task emoji assignment ───────────────────── */
function getTaskEmoji(title = "", category = "") {
  const t = (title || "").toLowerCase();
  if (t.includes("massage") || t.includes("scalp")) return "💆";
  if (t.includes("shampoo")) return "🧴";
  if (t.includes("serum") || t.includes("growth")) return "💊";
  if (t.includes("oil")) return "🫙";
  if (t.includes("braid") || t.includes("comb")) return "💇";
  if (t.includes("water") || t.includes("hydrat")) return "💧";
  if (t.includes("meditat") || t.includes("breath")) return "🧘";
  if (t.includes("protein") || t.includes("diet")) return "🥗";
  if (t.includes("consult") || t.includes("dermat")) return "👨‍⚕️";
  if (t.includes("sleep")) return "😴";
  if (t.includes("detangle")) return "💇";
  if (category === "morning") return "🌅";
  if (category === "night") return "🌙";
  return "✅";
}

/**
 * After a successful analyze — call Python /adaptive-routine,
 * save personalised tasks with emojis into UserIntelligence for today.
 */
async function _autoGenerateRoutine(userId, finalResult) {
  try {
    const today = new Date().toISOString().split("T")[0];
    const hairlossSev = finalResult.hairloss?.overallSeverity || "moderate";
    const dandruffSev = finalResult.dandruff?.severity || "moderate";
    const rootCause = finalResult.rootCause?.primary || "general";
    const lifestyleScore =
      finalResult.lifestyle?.overallScore ??
      finalResult.lifestyle?.overall_score ??
      50;
    const healthScore = finalResult.health?.score ?? 50;

    const pyRes = await axios.post(
      `${PYTHON_AI_URL}/adaptive-routine`,
      {
        hairlossSeverity: hairlossSev,
        dandruffSeverity: dandruffSev,
        rootCause,
        lifestyleScore,
        healthScore,
        humidity: "normal",
        pollutionLevel: "moderate",
      },
      { timeout: 15000 },
    );

    const routineData = pyRes.data?.routine || pyRes.data || {};
    const flatTasks = [];

    for (const [slot, items] of Object.entries(routineData)) {
      if (Array.isArray(items)) {
        items.forEach((t) => {
          const title = t.task || t.title || t.name || "Task";
          flatTasks.push({
            title,
            category: slot === "mid_day" ? "daily" : slot,
            emoji: getTaskEmoji(title, slot),
            xp: t.xp ?? 10,
            completed: false,
            completedAt: null,
          });
        });
      }
    }

    if (flatTasks.length === 0) return;

    let intel = await UserIntelligence.findOne({ userId });
    if (!intel) intel = await UserIntelligence.create({ userId });

    const idx = intel.routines.findIndex((r) => r.date === today);
    if (idx >= 0) {
      intel.routines[idx].tasks = flatTasks;
      intel.routines[idx].allDone = false;
      intel.routines[idx].totalXP = 0;
    } else {
      intel.routines.push({
        date: today,
        tasks: flatTasks,
        totalXP: 0,
        allDone: false,
        adherenceScore: 0,
      });
    }
    await intel.save();

    console.log(
      `[Routine] ✅ Auto-generated ${flatTasks.length} personalised tasks for user ${userId}`,
    );
  } catch (err) {
    console.error("[Routine] Auto-generate error:", err.message);
  }
}

/* ═══════════════════════════════════════════════════
   FLASHCARDS API
═══════════════════════════════════════════════════ */
app.get("/api/flashcards", async (req, res) => {
  try {
    const { userId } = req.query;
    const cards = await Flashcard.find().sort({ createdAt: 1 }).lean();

    if (!userId) {
      return res.json({ success: true, data: cards });
    }

    const userAnswers = await UserAnswer.findOne({ userId }).lean();
    const merged = cards.map((card) => {
      const match = userAnswers?.answers?.find(
        (a) => a.cardId === card._id.toString(),
      );
      return { ...card, selectedAnswer: match?.selectedAnswer ?? [] };
    });
    res.json({ success: true, data: merged });
  } catch (err) {
    console.error("Fetch flashcards error:", err);
    res.status(500).json({ success: false });
  }
});

app.post("/api/flashcards/answer", authenticateUser, async (req, res) => {
  try {
    const userId = req.user._id;
    const { cardId, question, selectedAnswer } = req.body;

    if (
      !cardId ||
      !question ||
      !Array.isArray(selectedAnswer) ||
      selectedAnswer.length !== 1
    ) {
      return res.status(400).json({
        success: false,
        message: "cardId, question, and exactly one selectedAnswer required",
      });
    }

    const answer = {
      cardId: cardId.toString(),
      question: question.trim(),
      selectedAnswer: [String(selectedAnswer[0])],
    };

    const doc = await UserAnswer.findOne({ userId });
    if (!doc) {
      await UserAnswer.create({ userId, answers: [answer] });
      return res.json({ success: true });
    }
    const idx = doc.answers.findIndex((a) => a.cardId === answer.cardId);
    if (idx === -1) doc.answers.push(answer);
    else doc.answers[idx] = answer;
    await doc.save();
    return res.json({ success: true });
  } catch (err) {
    console.error("Single answer error:", err);
    res.status(500).json({ success: false });
  }
});

app.get("/api/ai/flashcard-mapping", async (req, res) => {
  const cards = await Flashcard.find(
    { active: true },
    { ruleKey: 1, version: 1 },
  ).lean();

  const mapping = {};
  const versions = {};
  for (const c of cards) {
    mapping[c._id.toString()] = c.ruleKey;
    versions[c.ruleKey] = Math.max(versions[c.ruleKey] || 0, c.version || 1);
  }
  res.json({ mapping, versions, updatedAt: new Date().toISOString() });
});

app.post(
  "/api/ai/recalculate-root-cause",
  authenticateUser,
  async (req, res) => {
    try {
      const { hairloss, dandruff, flashcardAnswers } = req.body;
      const aiResponse = await axios.post(
        `${PYTHON_AI_URL}/recalculate-root-cause`,
        { hairloss, dandruff, flashcardAnswers },
        { timeout: 60000 },
      );
      return res.json(aiResponse.data);
    } catch (err) {
      console.error("Recalculate root cause error:", err.message);
      return res.status(500).json({ success: false, error: err.message });
    }
  },
);

/* ═══════════════════════════════════════════════════
   AI ANALYZE — MULTI VIEW
═══════════════════════════════════════════════════ */
// ═══════════════════════════════════════════════════
// AI ANALYZE — S3 URL PIPELINE
// ═══════════════════════════════════════════════════

app.post("/api/ai/analyze", authenticateUser, async (req, res) => {
  const userId = req.user?._id;

  if (!userId) {
    return res.status(401).json({
      success: false,
      message: "Unauthorized",
    });
  }

  const { topImageUrl, frontImageUrl, backImageUrl } = req.body;

  if (!topImageUrl) {
    return res.status(400).json({
      success: false,
      message: "topImageUrl is required",
    });
  }

  let aiRecord;

  try {
    // ─────────────────────────────
    // Prevent concurrent analysis
    // ─────────────────────────────

    const existing = await AiResult.findOne({
      userId,
      status: "processing",
    });

    if (existing) {
      return res.status(400).json({
        success: false,
        message: "Analysis already running",
      });
    }

    const username = req.user?.username ?? userId.toString();

    // ─────────────────────────────
    // Create processing record
    // ─────────────────────────────

    try {

  aiRecord = await AiResult.create({
    userId,
    type: "hair_analysis",
    status: "processing",
    images: {
      top: topImageUrl,
      front: frontImageUrl || null,
      back: backImageUrl || null,
    },
  });

} catch (err) {

  if (err.code === 11000) {
    return res.status(400).json({
      success: false,
      message: "Analysis already running",
    });
  }

  throw err;
}

    // ─────────────────────────────
    // Load flashcard answers
    // ─────────────────────────────

    const userAnswers = await UserAnswer.findOne({ userId }).lean();

    const flashcardAnswers = {};

    if (userAnswers?.answers?.length) {
      for (const a of userAnswers.answers) {
        if (a.cardId && Array.isArray(a.selectedAnswer)) {
          flashcardAnswers[a.cardId.toString()] = a.selectedAnswer[0];
        }
      }
    }

    // ─────────────────────────────
    // Load previous scan
    // ─────────────────────────────

    let previousHairScore = null;
    let previousDandruffSeverity = null;

    const previousScan = await AiResult.findOne({
      userId,
      status: "completed",
    })
      .sort({ createdAt: -1 })
      .select("health dandruff")
      .lean();

    if (previousScan) {
      previousHairScore = previousScan.health?.score ?? null;

      previousDandruffSeverity = previousScan.dandruff?.severity ?? null;
    }

    // ─────────────────────────────
    // Call Python AI
    // ─────────────────────────────

    let aiResponse;

    try {
      aiResponse = await aiLimiter(() =>
        axios.post(
          `${PYTHON_AI_URL}/analyze`,
          {
            topImageUrl,
            frontImageUrl,
            backImageUrl,
            userId,
            username,
            flashcardAnswers,
            previousHairScore,
            previousDandruffSeverity,
          },
          { timeout: 30000 },
        ),
      );
    } catch (err) {
      console.error("AI server error:", err.message);

      await AiResult.findByIdAndUpdate(aiRecord._id, {
        status: "failed",
        error: err.message,
      });

      return res.status(500).json({
        success: false,
        message: "AI server unavailable",
      });
    }

    const data = aiResponse.data;

    if (!data || !data.success) {
      throw new Error("Invalid AI response");
    }

    // ─────────────────────────────
    // Save final result
    // ─────────────────────────────

    const finalResult = await AiResult.findByIdAndUpdate(
      aiRecord._id,
      {
        status: "completed",
        hairloss: data.hairloss || {},
        dandruff: data.dandruff || {},
        health: data.health || {},
        lifestyle: data.lifestyle || {},
        simulation: data.simulation || {},
        rootCause: data.rootCause || {},
        suggestions: data.suggestions || {},
        tipsAndRemedies: data.tipsAndRemedies || {},
        futureRisk: data.futureRisk || {},
        timeline: data.timeline || {},
        routine: data.routine || [],
        adaptiveRoutine: data.adaptiveRoutine || [],
        progress: data.progress ?? null,
        assistantContext: data.assistantContext || {},
        aiResponse: data,
        error: null,
      },
      { new: true, lean: true},
    );

    // ─────────────────────────────
    // Generate personalized routine
    // ─────────────────────────────

    await _autoGenerateRoutine(userId, finalResult);

    // ─────────────────────────────
    // Notify user
    // ─────────────────────────────

    const score = data.health?.score;

    notifService.add(
      userId.toString(),
      `🧬 Analysis complete! Score: ${score ?? "—"}/100. Check your personalised routine.`,
      "report",
    );

    return res.json({
      success: true,
      result: finalResult,
    });
  } catch (err) {
    console.error("AI ANALYZE ERROR:", err.message);

    if (aiRecord?._id) {
      await AiResult.findByIdAndUpdate(aiRecord._id, {
        status: "failed",
        error: err.message,
      });
    }

    return res.status(500).json({
      success: false,
      error: err.message,
    });
  }
});

/* ── HISTORY ─────────────────────────────────────── */
app.get("/api/ai/history", authenticateUser, async (req, res) => {
  try {
    const userId = req.user?._id;
    if (!userId) {
      return res.status(401).json({ success: false, message: "Unauthorized" });
    }

    const records = await AiResult.find({ userId, status: "completed" })
      .sort({ createdAt: -1 })
      .limit(20)
      .lean();

    if (!records || records.length === 0) {
      return res.status(200).json({ success: true, history: [] });
    }

    const history = records.map((record) => ({
      _id: record._id,
      createdAt: record.createdAt,
      hairloss: record.hairloss || {},
      dandruff: record.dandruff || {},
      health: record.health || {},
      lifestyle: record.lifestyle || {},
      simulation: record.simulation || {},
      rootCause: record.rootCause || {},
      suggestions: record.suggestions || {},
      tipsAndRemedies: record.tipsAndRemedies || {},
      futureRisk: record.futureRisk || {},
      timeline: record.timeline || {},
      routine: record.routine || [],
      adaptiveRoutine: record.adaptiveRoutine || [],
      progress: record.progress || {},
      images: record.images || {},
    }));

    return res.status(200).json({ success: true, history });
  } catch (err) {
    console.error("History fetch error:", err.message);
    return res
      .status(500)
      .json({ success: false, message: "Server error fetching history" });
  }
});

/* ── AI FACTS ──────────────────────────────────────── */
app.get("/api/ai/facts", authenticateUser, async (req, res) => {
  try {
    const pyRes = await axios.post(
      `${PYTHON_AI_URL}/awareness-facts`,
      {
        hairSeverity: req.query.hairSeverity,
        rootCause: req.query.rootCause,
      },
      { timeout: 15000 },
    );
    const pyData = pyRes.data?.facts || pyRes.data || {};
    const facts = [];
    const accentColors = [
      "0xFF4ECDC4",
      "0xFFFF8C42",
      "0xFFFF6B9D",
      "0xFF7B68EE",
      "0xFFFFD700",
      "0xFF00E676",
    ];
    const cardColors = [
      "0xFF001A18",
      "0xFF1A1200",
      "0xFF1A001A",
      "0xFF0F0F2A",
      "0xFF1A1500",
      "0xFF001A0A",
    ];
    const emojis = ["🧬", "✂️", "🦴", "💧", "👱", "🚿", "💆", "🥑"];
    let i = 0;
    for (const arr of [
      pyData.hair_growth_science || [],
      pyData.scalp_biology || [],
      pyData.lifestyle_impact || [],
      pyData.medical_truths || [],
    ]) {
      for (const f of arr) {
        facts.push({
          title: f.title || f.statement || "",
          description: f.description || f.explanation || "",
          fullDetail: f.detail || f.explanation || f.description || "",
          emoji: emojis[i % emojis.length],
          accentColor: accentColors[i % accentColors.length],
          cardColor: cardColors[i % cardColors.length],
        });
        i++;
      }
    }
    for (const m of pyData.myth_busters || []) {
      facts.push({
        title: m.statement || "",
        description: m.explanation || "",
        fullDetail: m.explanation || "",
        emoji: "❓",
        accentColor: "0xFF9B30FF",
        cardColor: "0xFF1A0820",
      });
    }
    if (facts.length === 0) {
      facts.push(
        {
          title: "Hair Growth Happens in Cycles",
          description:
            "Hair grows in three phases: Anagen, Catagen, and Telogen.",
          fullDetail:
            "The anagen phase lasts 2-6 years. At any time, 85-90% of your hair is in the growing phase.",
          emoji: "🧬",
          accentColor: "0xFF4ECDC4",
          cardColor: "0xFF001A18",
        },
        {
          title: "50–150 Hairs Lost Daily is Normal",
          description:
            "Daily shedding is part of the natural hair growth cycle.",
          fullDetail:
            "Each follicle cycles independently. Temporary shedding can increase due to stress or diet.",
          emoji: "🚿",
          accentColor: "0xFF00E676",
          cardColor: "0xFF001A0A",
        },
      );
    }
    return res.json({ success: true, facts });
  } catch (err) {
    console.error("AI facts error:", err.message);
    return res
      .status(500)
      .json({ success: false, error: err.message, facts: [] });
  }
});

/* ── LEGACY ASSISTANT PROXY (behavioral coaching) ────── */
app.post("/api/assistant-legacy", authenticateUser, async (req, res) => {
  try {
    const payload = req.body;
    const pyRes = await axios.post(`${PYTHON_AI_URL}/assistant`, payload, {
      timeout: 30000,
    });
    return res.json(pyRes.data);
  } catch (err) {
    console.error("Assistant proxy error:", err.message);
    return res.status(500).json({ success: false, error: err.message });
  }
});

/* ═══════════════════════════════════════════════════
   IN-APP NOTIFICATIONS  (real store, NOT mobile push)
═══════════════════════════════════════════════════ */
app.get("/api/notifications", authenticateUser, (req, res) => {
  return res.json(notifService.getAll(req.user?._id?.toString()));
});

app.patch("/api/notifications/:id/read", authenticateUser, (req, res) => {
  notifService.markRead(req.user?._id?.toString(), req.params.id);
  return res.json({ success: true });
});

app.patch("/api/notifications/read-all", authenticateUser, (req, res) => {
  notifService.markAllRead(req.user?._id?.toString());
  return res.json({ success: true });
});

/* ── LATEST REPORT ───────────────────────────────── */
app.get("/api/ai/latest", authenticateUser, async (req, res) => {
  try {

    const userId = req.user._id;

    const result = await AiResult.findOne({ userId })
      .sort({ createdAt: -1 });

    if (!result) {
      return res.json({
        success: true,
        status: "none",
        result: null
      });
    }

    return res.json({
      success: true,
      status: result.status,
      result
    });

  } catch (error) {

    console.error("Get latest report error:", error);

    return res.status(500).json({
      success: false,
      message: "Server error"
    });

  }
});

/* ── HEALTH / TEST ───────────────────────────────── */
app.get("/api/test", (req, res) => {
  res.json({ success: true, message: "API working" });
});

app.get("/health", (req, res) => {
  res.status(200).json({ status: "ok" });
});

/* ── START ───────────────────────────────────────── */
app.listen(PORT, "0.0.0.0", () => {
  console.log(`Node server running on port ${PORT}`);
  console.log(`Local:           http://127.0.0.1:${PORT}`);
  console.log(`Android emu:     http://10.0.2.2:${PORT}`);
  console.log(`Physical device: http://192.168.1.12:${PORT}`);
});
