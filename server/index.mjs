// Leaderboard API for Daily Metahunt (and a static file server for local dev).
//
//   node server/index.mjs            # http://localhost:8791, in-memory scores
//   DATABASE_URL=postgres://... node server/index.mjs
//
// Answers are verified here against the same salted hashes the site uses, so
// a solve only counts if the player actually sent the right word. Times are
// measured from the round's release (00:00 UTC on its date).
import { createServer } from "node:http";
import { createHash, randomBytes } from "node:crypto";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";
import { createStore } from "./store.mjs";

const ROOT = join(fileURLToPath(new URL(".", import.meta.url)), "..");
const DOCS = join(ROOT, "docs");
const PORT = Number(process.env.PORT || process.argv[2] || 8791);
const STATIC_BASE = (process.env.STATIC_BASE || "https://daily-metahunt.onrender.com").replace(/\/$/, "");
const SERVE_STATIC = process.env.SERVE_STATIC !== "0";
const HINT_PENALTY = 300; // seconds per hint
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".json": "application/json" };

const store = await createStore(process.env.DATABASE_URL);
const sha = (s) => createHash("sha256").update(s).digest("hex");
const LEVELS = ["hard", "medium", "easy"];
const level = (d) => (LEVELS.includes(d) ? d : "hard");
const norm = (s) => String(s || "").toUpperCase().replace(/[^A-Z]/g, "");

// ---------- puzzle lookup (local files first, then the live static site) ----------
const puzzleCache = new Map();
async function loadRound(date, difficulty) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !LEVELS.includes(difficulty)) return null;
  const rel = difficulty === "hard" ? `puzzles/${date}.json` : `puzzles/${difficulty}/${date}.json`;
  const hit = puzzleCache.get(rel);
  if (hit && Date.now() - hit.at < 10 * 60e3) return hit.round;
  let round = null;
  try {
    round = JSON.parse(await readFile(join(DOCS, rel), "utf8"));
  } catch {
    try {
      const r = await fetch(`${STATIC_BASE}/${rel}`);
      if (r.ok) round = await r.json();
    } catch {}
  }
  if (round) puzzleCache.set(rel, { round, at: Date.now() });
  return round;
}

// ---------- tiny rate limiter ----------
const buckets = new Map();
function limited(key, perMinute) {
  const now = Date.now();
  const b = buckets.get(key) || { n: 0, reset: now + 60e3 };
  if (now > b.reset) { b.n = 0; b.reset = now + 60e3; }
  b.n++;
  buckets.set(key, b);
  if (buckets.size > 50000) buckets.clear();
  return b.n > perMinute;
}

// ---------- helpers ----------
function send(res, status, body) {
  res.writeHead(status, {
    "content-type": "application/json",
    "access-control-allow-origin": "*",
    "access-control-allow-headers": "content-type",
    "access-control-allow-methods": "GET, POST, OPTIONS",
    "cache-control": "no-store",
  });
  res.end(JSON.stringify(body));
}

async function readBody(req) {
  let raw = "";
  for await (const chunk of req) {
    raw += chunk;
    if (raw.length > 10_000) throw new Error("too large");
  }
  return raw ? JSON.parse(raw) : {};
}

async function playerFrom(body) {
  if (typeof body.token !== "string" || body.token.length < 20) return null;
  return store.playerByTokenHash(sha(body.token));
}

const releaseTime = (date) => Date.parse(date + "T00:00:00Z");

// ---------- routes ----------
async function api(req, res, url) {
  const ip = (req.headers["x-forwarded-for"] || req.socket.remoteAddress || "").split(",")[0].trim();
  if (req.method === "OPTIONS") return send(res, 204, {});
  if (limited("ip:" + ip, 120)) return send(res, 429, { error: "Slow down a little." });

  if (url.pathname === "/api/health") return send(res, 200, { ok: true, store: store.kind });

  if (url.pathname === "/api/players" && req.method === "POST") {
    if (limited("join:" + ip, 5)) return send(res, 429, { error: "Too many sign-ups from here." });
    const body = await readBody(req);
    const name = String(body.name || "").trim().replace(/\s+/g, " ");
    if (!/^[\p{L}\p{N} _.'-]{2,24}$/u.test(name)) {
      return send(res, 400, { error: "Names are 2–24 letters, numbers, spaces, or _ . ' -" });
    }
    const token = randomBytes(24).toString("base64url");
    const player = await store.createPlayer(name, sha(token));
    if (!player) return send(res, 409, { error: "That name is taken." });
    return send(res, 200, { name: player.name, token });
  }

  if (url.pathname === "/api/start" && req.method === "POST") {
    const body = await readBody(req);
    const player = await playerFrom(body);
    if (!player) return send(res, 401, { error: "Unknown player; join the leaderboard again." });
    const difficulty = level(body.difficulty);
    const round = await loadRound(String(body.date), difficulty);
    if (!round) return send(res, 404, { error: "No such round." });
    const at = await store.recordStart({ playerId: player.id, date: round.date, difficulty });
    return send(res, 200, { startedAt: at });
  }

  // Public, read-only: one player's run on one round (powers verified share links).
  if (url.pathname === "/api/run" && req.method === "GET") {
    const difficulty = level(url.searchParams.get("difficulty"));
    const date = url.searchParams.get("date") || "";
    const player = await store.playerByName(url.searchParams.get("name") || "");
    const round = await loadRound(date, difficulty);
    if (!player || !round) return send(res, 404, { error: "No such run." });
    const run = await store.run(player.id, date, difficulty);
    const rel = releaseTime(date);
    const secs = (t) => (t == null ? null : Math.max(0, Math.round((t - rel) / 1000)));
    return send(res, 200, {
      name: player.name, date, difficulty, round: round.round,
      started: secs(run.startedAt),
      solves: Object.fromEntries(Object.entries(run.solves).map(([k, t]) => [k, secs(t)])),
      personal: run.startedAt && run.solves.meta ? Math.round((run.solves.meta - run.startedAt) / 1000) : null,
      hints: run.hints,
    });
  }

  // Public, read-only: a player's stored history across rounds.
  if (url.pathname === "/api/player" && req.method === "GET") {
    const player = await store.playerByName(url.searchParams.get("name") || "");
    if (!player) return send(res, 404, { error: "No such player." });
    const rounds = (await store.history(player.id)).map((r) => ({
      date: r.date, difficulty: r.difficulty, feeders: r.feeders, hints: r.hints, meta: r.metaAt != null,
      sinceRelease: r.metaAt != null ? Math.max(0, Math.round((r.metaAt - releaseTime(r.date)) / 1000)) : null,
      personal: r.metaAt != null && r.startedAt != null ? Math.round((r.metaAt - r.startedAt) / 1000) : null,
    }));
    const metas = rounds.filter((r) => r.meta);
    const personal = metas.map((r) => r.personal).filter((x) => x != null);
    return send(res, 200, {
      name: player.name,
      rounds,
      totals: {
        metas: metas.length,
        hard: metas.filter((r) => r.difficulty === "hard").length,
        medium: metas.filter((r) => r.difficulty === "medium").length,
        easy: metas.filter((r) => r.difficulty === "easy").length,
        best: personal.length ? Math.min(...personal) : null,
        average: personal.length ? Math.round(personal.reduce((a, b) => a + b, 0) / personal.length) : null,
      },
    });
  }

  if ((url.pathname === "/api/solve" || url.pathname === "/api/hint") && req.method === "POST") {
    const body = await readBody(req);
    const player = await playerFrom(body);
    if (!player) return send(res, 401, { error: "Unknown player; join the leaderboard again." });
    const difficulty = level(body.difficulty);
    const round = await loadRound(String(body.date), difficulty);
    if (!round) return send(res, 404, { error: "No such round." });
    const which = body.puzzle === "meta" ? "meta" : Number(body.puzzle);
    const target = which === "meta" ? round.meta : round.puzzles.find((p) => p.id === which);
    if (!target) return send(res, 404, { error: "No such puzzle." });
    const key = { playerId: player.id, date: round.date, difficulty, puzzle: String(which) };

    if (url.pathname === "/api/hint") {
      await store.recordHint(key);
      return send(res, 200, { ok: true });
    }
    if (limited(`solve:${player.id}:${round.date}:${which}`, 20)) return send(res, 429, { error: "Too many guesses." });
    const salt = round.salt || round.date;
    if (sha(`metahunt|${salt}|${norm(body.answer)}`) !== target.hash) return send(res, 200, { correct: false });
    const at = await store.recordSolve(key);
    return send(res, 200, { correct: true, seconds: Math.max(0, Math.round((at - releaseTime(round.date)) / 1000)) });
  }

  if (url.pathname === "/api/leaderboard" && req.method === "GET") {
    const date = url.searchParams.get("date") || "";
    const difficulty = level(url.searchParams.get("difficulty"));
    const round = await loadRound(date, difficulty);
    if (!round) return send(res, 404, { error: "No such round." });
    const rows = (await store.roundRows(date, difficulty)).map((r) => {
      const seconds = r.metaAt ? Math.max(0, Math.round((r.metaAt - releaseTime(date)) / 1000)) : null;
      return {
        name: r.name,
        feeders: r.feeders,
        total: round.puzzles.length,
        meta: seconds !== null,
        seconds,
        hints: r.hints,
        score: seconds === null ? null : seconds + HINT_PENALTY * r.hints,
        personal: r.metaAt && r.startedAt ? Math.round((r.metaAt - r.startedAt) / 1000) : null,
      };
    });
    rows.sort((a, b) => (a.score ?? Infinity) - (b.score ?? Infinity) || b.feeders - a.feeders || a.hints - b.hints);
    return send(res, 200, { date, difficulty, hintPenalty: HINT_PENALTY, rows: rows.slice(0, 100) });
  }

  if (url.pathname === "/api/alltime" && req.method === "GET") {
    const difficulty = level(url.searchParams.get("difficulty"));
    return send(res, 200, { difficulty, rows: await store.allTime(difficulty) });
  }

  return send(res, 404, { error: "Not found." });
}

async function staticFile(req, res, url) {
  let path = normalize(decodeURIComponent(url.pathname)).replace(/^(\.\.[/\\])+/, "");
  if (path.endsWith("/")) path += "index.html";
  try {
    const body = await readFile(join(DOCS, path));
    res.writeHead(200, { "content-type": TYPES[extname(path)] || "application/octet-stream", "cache-control": "no-cache" });
    res.end(body);
  } catch {
    res.writeHead(404);
    res.end("not found");
  }
}

createServer(async (req, res) => {
  const url = new URL(req.url, "http://x");
  try {
    if (url.pathname.startsWith("/api/")) return await api(req, res, url);
    if (SERVE_STATIC) return await staticFile(req, res, url);
    send(res, 404, { error: "Not found." });
  } catch (e) {
    if (e.message === "too large") return send(res, 413, { error: "Request too large." });
    if (e instanceof SyntaxError) return send(res, 400, { error: "Malformed JSON." });
    console.error(e);
    send(res, 500, { error: "Server error." });
  }
}).listen(PORT, () => console.log(`metahunt server on http://localhost:${PORT} (${store.kind} store)`));
