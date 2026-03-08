const express = require("express");
const Groq = require("groq-sdk");
const fs = require("fs");

const router = express.Router();

const groq = new Groq({
  apiKey: process.env.GROQ_API_KEY,
});

//////////////////////////////////////////////////////////////
// Load Knowledge Base Safely
//////////////////////////////////////////////////////////////

let knowledgeRaw;

try {
  knowledgeRaw = JSON.parse(fs.readFileSync("./knowledge.json", "utf-8"));
} catch (err) {
  console.error("❌ Failed to load knowledge.json:", err.message);

  knowledgeRaw = {
    keyword_index: {},
    website_resources: [],
    youtube_videos: [],
  };
}

knowledgeRaw.keyword_index = knowledgeRaw.keyword_index || {};
knowledgeRaw.website_resources = knowledgeRaw.website_resources || [];
knowledgeRaw.youtube_videos = knowledgeRaw.youtube_videos || [];

//////////////////////////////////////////////////////////////
// Keyword Map Builder
//////////////////////////////////////////////////////////////

const keywordMap = {};

function addToMap(keyword, websiteIds = [], videoIds = []) {
  const key = keyword
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .trim();
  if (!key) return;

  if (!keywordMap[key]) {
    keywordMap[key] = {
      websiteIds: new Set(),
      videoIds: new Set(),
    };
  }

  websiteIds.forEach((id) => keywordMap[key].websiteIds.add(id));
  videoIds.forEach((id) => keywordMap[key].videoIds.add(id));
}

Object.entries(knowledgeRaw.keyword_index).forEach(([category, mapping]) => {
  const humanKey = category.replace(/_/g, " ");

  addToMap(category, mapping.websites || [], mapping.videos || []);
  addToMap(humanKey, mapping.websites || [], mapping.videos || []);
});

knowledgeRaw.website_resources.forEach((entry) => {
  if (!entry?.id) return;

  (entry.keywords || []).forEach((kw) => {
    addToMap(kw, [entry.id], []);
  });
});

knowledgeRaw.youtube_videos.forEach((video) => {
  if (!video?.id) return;

  const terms = [...(video.keywords || []), ...(video.tags || [])];

  terms.forEach((kw) => {
    addToMap(kw, [], [video.id]);
  });
});

const sortedKeywords = Object.keys(keywordMap).sort(
  (a, b) => b.length - a.length,
);

//////////////////////////////////////////////////////////////
// Helpers
//////////////////////////////////////////////////////////////

const normalize = (text) =>
  text
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

//////////////////////////////////////////////////////////////
// Keyword Matching
//////////////////////////////////////////////////////////////

function findReferences(message) {
  const msg = normalize(message);

  const matchedWebsiteIds = new Set();
  const matchedVideoIds = new Set();

  for (const kw of sortedKeywords) {
    if (msg.includes(kw)) {
      const entry = keywordMap[kw];

      entry.websiteIds.forEach((id) => matchedWebsiteIds.add(id));
      entry.videoIds.forEach((id) => matchedVideoIds.add(id));

      // stop after strong match
      if (matchedWebsiteIds.size || matchedVideoIds.size) break;
    }
  }

  return {
    websiteIds: matchedWebsiteIds,
    videoIds: matchedVideoIds,
  };
}

//////////////////////////////////////////////////////////////
// Website Source Name
//////////////////////////////////////////////////////////////

function deriveSourceName(url) {
  if (url.includes("aad.org")) return "American Academy of Dermatology";
  if (url.includes("mayoclinic.org")) return "Mayo Clinic";
  if (url.includes("nhs.uk")) return "NHS UK";
  if (url.includes("healthline.com")) return "Healthline";
  if (url.includes("webmd.com")) return "WebMD";

  return url;
}

//////////////////////////////////////////////////////////////
// YouTube Utilities
//////////////////////////////////////////////////////////////

function extractYouTubeId(url) {
  try {
    const parsed = new URL(url);

    if (parsed.hostname === "youtu.be") {
      return parsed.pathname.slice(1);
    }

    if (parsed.searchParams.get("v")) {
      return parsed.searchParams.get("v");
    }

    if (parsed.pathname.startsWith("/embed/")) {
      return parsed.pathname.split("/embed/")[1];
    }
  } catch (err) {}

  return null;
}

function buildYouTubeLinks(videoId) {
  return {
    videoId,
    watch_url: `https://www.youtube.com/watch?v=${videoId}`,
    embed_url: `https://www.youtube.com/embed/${videoId}`,
    thumbnail: `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`,
  };
}

//////////////////////////////////////////////////////////////
// Build References
//////////////////////////////////////////////////////////////

function buildRichReferences(websiteIds, videoIds, maxEach = 5) {
  const websitePool =
    websiteIds.size === 0
      ? knowledgeRaw.website_resources
      : knowledgeRaw.website_resources.filter((i) => websiteIds.has(i.id));

  const videoPool =
    videoIds.size === 0
      ? knowledgeRaw.youtube_videos
      : knowledgeRaw.youtube_videos.filter((v) => videoIds.has(v.id));

  //////////////////////////////////////////////////////////
  // Website References
  //////////////////////////////////////////////////////////

  const websiteRefs = websitePool
    .slice(0, maxEach)
    .flatMap((item) =>
      (item.urls || []).map((url) => ({
        type: "website",
        url,
        source: deriveSourceName(url),
      })),
    )
    .slice(0, maxEach);

  //////////////////////////////////////////////////////////
  // YouTube References (no duplicates)
  //////////////////////////////////////////////////////////

  const seenVideos = new Set();

  const videoRefs = videoPool
    .map((video) => {
      const videoId = extractYouTubeId(video.url || "");

      if (!videoId) return null;
      if (seenVideos.has(videoId)) return null;

      seenVideos.add(videoId);

      const ytLinks = buildYouTubeLinks(videoId);

      return {
        type: "youtube",
        title: video.title || "",
        channel: video.channel || "",
        credential: video.credential || "",
        duration_minutes: video.duration_minutes || 0,
        ...ytLinks,
      };
    })
    .filter(Boolean)
    .slice(0, maxEach);

  return { websiteRefs, videoRefs };
}

//////////////////////////////////////////////////////////////
// POST /api/chatbot
//////////////////////////////////////////////////////////////

router.post("/", async (req, res) => {
  try {
    const { message } = req.body;

    if (!message?.trim()) {
      return res.status(400).json({
        success: false,
        error: "Message is required",
      });
    }

    const { websiteIds, videoIds } = findReferences(message);

    const { websiteRefs, videoRefs } = buildRichReferences(
      websiteIds,
      videoIds,
    );

    /////////////////////////////////////////////////////////
    // GROQ LLM
    /////////////////////////////////////////////////////////

    const completion = await groq.chat.completions.create({
      model: "llama-3.3-70b-versatile",

      messages: [
        {
          role: "system",
          content: `
You are a certified haircare and scalp health expert.

Provide:
• Clear
• Structured
• Evidence-based advice

Rules:
- Answer directly
- Avoid unnecessary introductions
- Use bullet points where useful
- Bold important terms using *single asterisks*
- Do not mention YouTube unless asked
`.trim(),
        },

        {
          role: "user",
          content: message.trim(),
        },
      ],

      temperature: 0.4,
      max_tokens: 500,
    });

    const reply = completion?.choices?.[0]?.message?.content || "";

    /////////////////////////////////////////////////////////
    // Response
    /////////////////////////////////////////////////////////

    res.json({
      success: true,
      reply,
      references: {
        websites: websiteRefs,
        videos: videoRefs,
      },
    });
  } catch (err) {
    console.error("GROQ ERROR:", err);

    res.status(500).json({
      success: false,
      error: err.message,
    });
  }
});

module.exports = router;
