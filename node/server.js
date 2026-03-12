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

const MongoStore = require("connect-mongo").default;

app.use(
  session({
    secret: SESSION_SECRET,
    resave: false,
    saveUninitialized: false,

    store: MongoStore.create({
      mongoUrl: process.env.MONGO_URI,
      collectionName: "sessions",
    }),

    cookie: {
      maxAge: 1000 * 60 * 60 * 24 * 7,
    },
  })
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

/* ── S3 URL HELPERS ───────────────────────────── */

const S3_BASE_URL = `https://${process.env.AWS_BUCKET_NAME}.s3.${process.env.AWS_REGION}.amazonaws.com/`;

function buildS3Url(key) {
  if (!key) return null;

  // already full URL
  if (key.startsWith("http://") || key.startsWith("https://")) {
    return key;
  }

  return `${S3_BASE_URL}${key}`;
}

function attachImageUrls(result) {
  if (!result) return result;

  if (result.images) {
    result.images.top = buildS3Url(result.images.top);
    result.images.front = buildS3Url(result.images.front);
    result.images.back = buildS3Url(result.images.back);
  }

  if (result.hairloss?.overlayImageKey) {
    result.hairloss.overlayImageUrl = buildS3Url(
      result.hairloss.overlayImageKey,
    );
  }

  if (result.dandruff?.overlayImageKey) {
    result.dandruff.overlayImageUrl = buildS3Url(
      result.dandruff.overlayImageKey,
    );
  }

  return result;
}

app.post("/api/upload/presign", authenticateUser, async (req, res) => {
  try {
    const { filename, contentType, view } = req.body;
    const userId = req.user._id;

    if (!filename || !contentType || !view) {
      return res.status(400).json({
        success: false,
        message: "filename, contentType and view required",
      });
    }

    const key = `hair/${userId}/${view}/${uuidv4()}_${filename}`;

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
    res.status(500).json({ success: false });
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

// ═══════════════════════════════════════════════════
// AI ANALYZE — S3 URL PIPELINE
// ═══════════════════════════════════════════════════

app.post("/api/ai/analyze", authenticateUser, async (req, res) => {
  let aiRecord;

  try {
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

    const extractS3Key = (url) => {
      try {
        return new URL(url).pathname.substring(1);
      } catch {
        return null;
      }
    };

    const topImageKey = extractS3Key(topImageUrl);
    const frontImageKey = frontImageUrl ? extractS3Key(frontImageUrl) : null;
    const backImageKey = backImageUrl ? extractS3Key(backImageUrl) : null;

    const existing = await AiResult.findOne({
      userId,
      status: "processing",
    });

    if (existing) {
      const started = new Date(existing.createdAt).getTime();
      const now = Date.now();

      const MAX_PROCESS_TIME = 5 * 60 * 1000;

      if (now - started < MAX_PROCESS_TIME) {
        return res.status(400).json({
          success: false,
          message: "Analysis already running",
        });
      }

      await AiResult.updateOne(
        { _id: existing._id },
        { $set: { status: "failed", error: "Stale job reset" } },
      );
    }

    aiRecord = await AiResult.create({
      userId,
      type: "hair_analysis",
      status: "processing",
      images: {
        top: topImageKey,
        front: frontImageKey,
        back: backImageKey,
      },
    });

    // Load saved flashcard answers so Python can compute lifestyle risk
    let flashcardAnswers = {};
    try {
      const userAnswerDoc = await UserAnswer.findOne({ userId }).lean();
      if (userAnswerDoc?.answers?.length) {
        // Convert array [{cardId, question, selectedAnswer}] → { cardId: selectedAnswer[] }
        flashcardAnswers = Object.fromEntries(
          userAnswerDoc.answers.map((a) => [a.cardId, a.selectedAnswer])
        );
      }
    } catch (ansErr) {
      logger?.warn?.("Could not load flashcard answers:", ansErr.message);
    }

    const aiResponse = await aiLimiter(async () => {
      return axios.post(
        `${PYTHON_AI_URL}/analyze`,
        {
          topImageKey,
          frontImageKey,
          backImageKey,
          userId,
          flashcardAnswers,
        },
        { timeout: 120000 },
      );
    });

    const data = aiResponse.data;

    if (!data || !data.success) {
      throw new Error("Invalid AI response");
    }

    // ── Normalize Flask snake_case → Mongoose camelCase ──────────
    function normalizeHairloss(hl, healthBreakdown) {
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

      // Resolve combinedDamage: Python now sends it directly.
      // Fallback: pull from health.breakdown.hairloss.combined_damage
      let combinedDamage =
        hl.combinedDamage  ??
        hl.combined_damage ??
        healthBreakdown?.hairloss?.combined_damage ??
        null;

      // Last resort: compute weighted average from per-view damages
      if (combinedDamage === null || combinedDamage === undefined) {
        const top   = views.top?.damage   ?? null;
        const front = views.front?.damage ?? null;
        const back  = views.back?.damage  ?? null;
        if (top !== null && front !== null && back !== null) {
          combinedDamage = Math.round(top * 0.5 + front * 0.3 + back * 0.2);
        }
      }

      return {
        overallSeverity: hl.overallSeverity ?? hl.overall_severity ?? "unknown",
        combinedDamage,
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
        // Short keys (legacy Flutter reads rc.primary / rc.secondary)
        primary:            rc.primary            ?? rc.primary_cause    ?? rc.primaryCause   ?? null,
        secondary:          rc.secondary          ?? rc.secondary_cause  ?? rc.secondaryCause ?? null,
        // Full Bayesian fields (BayesianRootCause.fromJson in Flutter)
        primary_cause:      rc.primary_cause      ?? rc.primary          ?? null,
        secondary_cause:    rc.secondary_cause    ?? rc.secondary        ?? null,
        confidence_percent: rc.confidence_percent ?? rc.confidence       ?? 0,
        causes:             rc.causes             ?? [],
        impact_breakdown:   rc.impact_breakdown   ?? rc.details          ?? {},
        details:            rc.impact_breakdown   ?? rc.details          ?? {},
        data_strength:      rc.data_strength      ?? "Moderate",
        network_summary:    rc.network_summary    ?? "",
      };
    }

    const normalizedHairloss  = normalizeHairloss(data.hairloss, data.health?.breakdown);
    const normalizedRootCause = normalizeRootCause(data.rootCause);

    let finalResult = await AiResult.findByIdAndUpdate(
      aiRecord._id,
      {
        status: "completed",
        hairloss: normalizedHairloss,
        dandruff: data.dandruff || {},
        health: data.health || {},
        lifestyle: data.lifestyle || {},
        rootCause: normalizedRootCause,
        simulation: data.simulation || {},
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
      { new: true, lean: true },
    );

    finalResult = attachImageUrls(finalResult);
    // auto-generate personalised routine
    await _autoGenerateRoutine(userId, finalResult);

    return res.json({
      success: true,
      result: finalResult,
    });
  } catch (err) {
    console.error("AI ANALYZE ERROR:", err);

    if (aiRecord?._id) {
      await AiResult.updateOne(
        { _id: aiRecord._id },
        { $set: { status: "failed", error: err.message } },
      );
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

    const history = records.map((record) => attachImageUrls(record));

    return res.status(200).json({ success: true, history });
  } catch (err) {
    console.error("History fetch error:", err.message);

    return res.status(500).json({
      success: false,
      message: "Server error fetching history",
    });
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

    let result = await AiResult.findOne({ userId })
      .sort({ createdAt: -1 })
      .lean();

    if (!result) {
      return res.json({
        success: true,
        status: "none",
        result: null,
      });
    }

    result = attachImageUrls(result);

    return res.json({
      success: true,
      status: result.status,
      result,
    });
  } catch (error) {
    console.error("Get latest report error:", error);

    return res.status(500).json({
      success: false,
      message: "Server error",
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