/**
 * seedHairKnowledge.js
 * Path: backend/node/scripts/seedHairKnowledge.js
 *
 * One-time script — reads hairKnowledge.json and upserts every category
 * into the HairKnowledgeSystem MongoDB collection.
 *
 * Run once:
 *   node scripts/seedHairKnowledge.js
 *
 * Safe to re-run — uses upsert so existing docs are updated, not duplicated.
 */

const path    = require("path");
const fs      = require("fs");
const mongoose = require("mongoose");

// ── Load model ────────────────────────────────────────────────────────────────
const HairKnowledgeSystem = require("../models/HairKnowledgeSystem");

// ── Resolve the JSON source file ──────────────────────────────────────────────
const DATA_FILE = path.join(__dirname, "..", "data", "hairKnowledge.json");

// ── MongoDB connection string — reads from .env or falls back to localhost ───
require("dotenv").config({ path: path.join(__dirname, "..", ".env") });
const MONGO_URI = process.env.MONGO_URI || process.env.MONGODB_URI || "mongodb://127.0.0.1:27017/hairai";

// ─────────────────────────────────────────────────────────────────────────────

async function seed() {
  console.log("\n╔══════════════════════════════════════════╗");
  console.log("║      HairKnowledgeSystem Seed Script     ║");
  console.log("╚══════════════════════════════════════════╝\n");

  // ── 1. Read JSON file ──────────────────────────────────────────────────────
  if (!fs.existsSync(DATA_FILE)) {
    console.error("❌  File not found:", DATA_FILE);
    console.error("    Place your hairKnowledge.json at that path and retry.");
    process.exit(1);
  }

  let categories;
  try {
    const raw = fs.readFileSync(DATA_FILE, "utf8");
    categories = JSON.parse(raw);
  } catch (err) {
    console.error("❌  Failed to parse hairKnowledge.json:", err.message);
    process.exit(1);
  }

  if (!Array.isArray(categories) || categories.length === 0) {
    console.error("❌  hairKnowledge.json must be a non-empty array of category objects.");
    process.exit(1);
  }

  console.log(`📂  Source file : ${DATA_FILE}`);
  console.log(`📦  Categories  : ${categories.length}`);
  console.log(`📋  Total facts : ${categories.reduce((n, c) => n + (c.facts?.length || 0), 0)}\n`);

  // ── 2. Connect to MongoDB ──────────────────────────────────────────────────
  console.log(`🔌  Connecting to MongoDB...`);
  try {
    await mongoose.connect(MONGO_URI, {
      useNewUrlParser:    true,
      useUnifiedTopology: true,
    });
    console.log(`✅  Connected: ${MONGO_URI}\n`);
  } catch (err) {
    console.error("❌  MongoDB connection failed:", err.message);
    process.exit(1);
  }

  // ── 3. Upsert each category ────────────────────────────────────────────────
  let inserted = 0;
  let updated  = 0;
  let errors   = 0;

  for (const cat of categories) {
    if (!cat.category) {
      console.warn(`⚠️   Skipping entry without a "category" field:`, JSON.stringify(cat).slice(0, 80));
      errors++;
      continue;
    }

    // Normalise facts — ensure required fields have fallbacks so Mongoose
    // doesn't reject documents with partial data from the JSON file.
    const facts = (cat.facts || []).map((f) => ({
      title:         f.title        || "Untitled",
      description:   f.description  || "",
      fullDetail:    f.fullDetail   || f.description || "",
      emoji:         f.emoji,
      accentColor:   f.accentColor,
      cardColor:     f.cardColor,
      learningLevel: f.learningLevel ?? 1,
      isMythBuster:  f.isMythBuster  ?? false,
      mythStatement: f.mythStatement,
      isTruth:       f.isTruth,
      severityLevel: f.severityLevel || "moderate",
      tags:          f.tags          || [],
      quizOptions:   f.quizOptions   || [],
      correctAnswer: f.correctAnswer,
      evidence:      f.evidence,
    }));

    try {
      const result = await HairKnowledgeSystem.findOneAndUpdate(
        { category: cat.category },           // match by category name
        {
          $set: {
            category: cat.category,
            facts,
            isActive: cat.isActive !== false, // default true unless explicitly false
          },
        },
        { upsert: true, new: true, runValidators: true }
      );

      const wasInserted = !result._id || result.isNew;
      if (wasInserted) {
        console.log(`  ➕  Inserted  "${cat.category}" — ${facts.length} facts`);
        inserted++;
      } else {
        console.log(`  🔄  Updated   "${cat.category}" — ${facts.length} facts`);
        updated++;
      }
    } catch (err) {
      console.error(`  ❌  Failed    "${cat.category}": ${err.message}`);
      errors++;
    }
  }

  // ── 4. Summary ─────────────────────────────────────────────────────────────
  console.log("\n─────────────────────────────────────────");
  console.log(`  ✅  Inserted : ${inserted}`);
  console.log(`  🔄  Updated  : ${updated}`);
  console.log(`  ❌  Errors   : ${errors}`);
  console.log("─────────────────────────────────────────");

  const total = await HairKnowledgeSystem.countDocuments();
  console.log(`\n📊  HairKnowledgeSystem now has ${total} category document(s) in MongoDB.\n`);

  await mongoose.disconnect();
  console.log("🔌  Disconnected. Seed complete.\n");
  process.exit(errors > 0 ? 1 : 0);
}

seed().catch((err) => {
  console.error("Unexpected error:", err);
  process.exit(1);
});