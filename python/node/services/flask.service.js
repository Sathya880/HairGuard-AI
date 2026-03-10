const axios = require("axios");

/*
────────────────────────────────────────
FLASK BASE URL
────────────────────────────────────────
Uses environment variable if present
Fallback → local Flask server
*/

const FLASK_BASE_URL =
  process.env.FLASK_URL ||
  process.env.PYTHON_AI_URL ||
  "https://hairguard-ai.onrender.com";

/*
────────────────────────────────────────
AXIOS CLIENT
────────────────────────────────────────
*/

const api = axios.create({
  baseURL: FLASK_BASE_URL,
  timeout: 180000,
  headers: {
    "Content-Type": "application/json",
  },
});

/*
────────────────────────────────────────
AI ANALYSIS
/image + lifestyle analysis
────────────────────────────────────────
*/

exports.callAnalyze = async (payload) => {
  try {
    const { data } = await api.post("/analyze", payload);
    return data;
  } catch (error) {
    console.error("[Flask] Analyze error:", error.message);

    if (error.response) {
      console.error("[Flask] Response:", error.response.data);
    }

    throw new Error("AI analysis service unavailable");
  }
};

/*
────────────────────────────────────────
AI ASSISTANT CHAT
Used by /assistant/chat route
────────────────────────────────────────
*/

exports.callAssistant = async (payload) => {
  try {
    const { data } = await api.post("/assistant", payload);
    return data;
  } catch (error) {
    console.error("[Flask] Assistant error:", error.message);

    if (error.response) {
      console.error("[Flask] Response:", error.response.data);
    }

    throw new Error("AI assistant service unavailable");
  }
};

/*
────────────────────────────────────────
HEALTH CHECK (optional but useful)
────────────────────────────────────────
*/

exports.checkFlaskHealth = async () => {
  try {
    const { data } = await api.get("/health");
    return data;
  } catch (error) {
    console.error("[Flask] Health check failed:", error.message);
    return { status: "down" };
  }
};