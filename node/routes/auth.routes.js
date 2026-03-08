const express = require("express");
const passport = require("passport");
const jwt = require("jsonwebtoken");
const User = require("../models/User");

const router = express.Router();

/* ============================================
   🔐 Helper: Generate JWT
============================================ */

const generateToken = (user) => {
  if (!process.env.JWT_SECRET) {
    throw new Error("JWT_SECRET is not defined");
  }

  return jwt.sign(
    { _id: user._id }, // keep payload minimal
    process.env.JWT_SECRET,
    { expiresIn: "7d" }
  );
};

/* ============================================
   🔎 CHECK USERNAME
============================================ */

router.get("/check-username", async (req, res) => {
  try {
    const { username } = req.query;

    if (!username) {
      return res.json({ success: false, exists: false });
    }

    const user = await User.findOne({ username });

    return res.json({
      success: true,
      exists: !!user,
    });

  } catch (err) {
    console.error("CHECK USERNAME ERROR:", err);
    return res.status(500).json({
      success: false,
      message: "Server error",
    });
  }
});

/* ============================================
   📝 SIGNUP
============================================ */

router.post("/signup", async (req, res) => {
  try {
    const { name, username, password, age, gender } = req.body;

    if (!name || !username || !password || !age || !gender) {
      return res.status(400).json({
        success: false,
        message: "All fields are required",
      });
    }

    if (age < 10 || age > 25) {
      return res.status(400).json({
        success: false,
        message: "Age must be between 10 and 25",
      });
    }

    if (!["Male", "Female"].includes(gender)) {
      return res.status(400).json({
        success: false,
        message: "Invalid gender",
      });
    }

    const existingUser = await User.findOne({ username });

    if (existingUser) {
      return res.status(400).json({
        success: false,
        message: "Username already exists",
      });
    }

    const user = new User({
      name,
      username,
      age,
      gender,
    });

    await User.register(user, password);

    const token = generateToken(user);

    return res.status(201).json({
      success: true,
      token,
      user: {
        _id: user._id,
        name: user.name,
        username: user.username,
        age: user.age,
        gender: user.gender,
      },
    });

  } catch (err) {
    console.error("SIGNUP ERROR:", err);

    return res.status(500).json({
      success: false,
      message: "Server error",
    });
  }
});

/* ============================================
   🔑 LOGIN
============================================ */

router.post("/login", (req, res, next) => {

  passport.authenticate("local", async (err, user) => {

    if (err) {
      console.error("LOGIN ERROR:", err);
      return res.status(500).json({
        success: false,
        message: "Server error",
      });
    }

    if (!user) {
      return res.status(400).json({
        success: false,
        message: "Invalid username or password",
      });
    }

    const token = generateToken(user);

    return res.json({
      success: true,
      token,
      user: {
        _id: user._id,
        name: user.name,
        username: user.username,
        age: user.age,
        gender: user.gender,
      },
    });

  })(req, res, next);
});

module.exports = router;