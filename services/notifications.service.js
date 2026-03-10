/**
 * notifications.service.js
 *
 * In-app notification store (in-memory, per user).
 * Displayed inside the app bell icon only — no mobile push.
 *
 * Usage:
 *   const notifService = require('./services/notifications.service');
 *   notifService.add(userId, '🔥 Streak started!', 'streak');
 *   notifService.getAll(userId);       // → Array (newest first)
 *   notifService.markRead(userId, id);
 *   notifService.markAllRead(userId);
 */

const { v4: uuidv4 } = require('uuid');

const _store       = new Map();   // Map<userId:string, Notification[]>
const MAX_PER_USER = 50;

function _key(userId)    { return userId ? userId.toString() : 'anonymous'; }
function _bucket(userId) {
  const k = _key(userId);
  if (!_store.has(k)) _store.set(k, []);
  return _store.get(k);
}

/**
 * Add a notification.
 * @param {string|ObjectId} userId
 * @param {string}          message  Text shown in the bell panel
 * @param {string}          [type]   'routine'|'streak'|'report'|'reward'|'general'
 */
function add(userId, message, type = 'general') {
  const bucket = _bucket(userId);
  const now    = new Date().toISOString();
  const id     = uuidv4();

  const notif = { _id: id, id, title: message, message, type,
                  isRead: false, createdAt: now, time: now };

  bucket.unshift(notif);
  if (bucket.length > MAX_PER_USER) bucket.splice(MAX_PER_USER);
  return notif;
}

function getAll(userId)              { return _bucket(userId); }
function markRead(userId, notifId)   {
  const n = _bucket(userId).find(n => n._id === notifId || n.id === notifId);
  if (n) { n.isRead = true; return true; }
  return false;
}
function markAllRead(userId)         { _bucket(userId).forEach(n => { n.isRead = true; }); }

module.exports = { add, getAll, markRead, markAllRead };