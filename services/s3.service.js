// s3.service.js
require("dotenv").config();

const AWS = require("aws-sdk");
const path = require("path");
const crypto = require("crypto");

const {
  AWS_ACCESS_KEY_ID,
  AWS_SECRET_ACCESS_KEY,
  AWS_REGION,
  AWS_BUCKET_NAME,
} = process.env;

if (!AWS_ACCESS_KEY_ID || !AWS_SECRET_ACCESS_KEY || !AWS_REGION) {
  throw new Error("Missing AWS credentials in env");
}

if (!AWS_BUCKET_NAME) {
  throw new Error("AWS_BUCKET_NAME missing");
}

// =====================================================
// S3 CLIENT (ACL DISABLED AT BUCKET LEVEL)
// =====================================================
const s3 = new AWS.S3({
  accessKeyId: AWS_ACCESS_KEY_ID,
  secretAccessKey: AWS_SECRET_ACCESS_KEY,
  region: AWS_REGION,
  signatureVersion: "v4",
});

// =====================================================
// HELPERS
// =====================================================
function sanitizeFolder(folder) {
  return folder.replace(/[^a-zA-Z0-9/_-]/g, "_");
}

function generateKey(folder, originalName = "image.jpg") {
  const ext = path.extname(originalName) || ".jpg";
  const id = crypto.randomBytes(8).toString("hex");
  const safeFolder = sanitizeFolder(folder);
  return `${safeFolder}/${Date.now()}-${id}${ext}`;
}

// =====================================================
// UPLOAD (NO ACL ❗)
// =====================================================
async function uploadToS3(file, folder) {
  if (!file?.buffer) throw new Error("Invalid file buffer");
  if (!folder) throw new Error("Folder required");

  const key = generateKey(folder, file.originalname);

  await s3.putObject({
    Bucket: AWS_BUCKET_NAME,
    Key: key,
    Body: file.buffer,
    ContentType: file.mimetype || "image/jpeg",
    CacheControl: "public, max-age=31536000",
  }).promise();

  return `https://${AWS_BUCKET_NAME}.s3.${AWS_REGION}.amazonaws.com/${key}`;
}

// =====================================================
// DELETE
// =====================================================
async function deleteFromS3(key) {
  if (!key) return;
  await s3.deleteObject({
    Bucket: AWS_BUCKET_NAME,
    Key: key,
  }).promise();
}

module.exports = {
  uploadToS3,
  deleteFromS3,
};
