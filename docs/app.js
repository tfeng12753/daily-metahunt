(() => {
  const $ = (s) => document.querySelector(s);
  const el = (tag, cls, text) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  };
  const SVG = "http://www.w3.org/2000/svg";
  const svg = (tag, attrs) => {
    const e = document.createElementNS(SVG, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    return e;
  };

  let index = null;
  let puzzle = null;
  let difficulty = "hard";
  const rk = () => puzzle.salt || puzzle.date; // "2026-09-28", "2026-09-28/medium" or "2026-09-28/easy"
  const LEVEL = { easy: "Easy", medium: "Medium", hard: "Hard" };
  const levelPath = (dir, date, diff) => (diff === "hard" ? `${dir}/${date}.json` : `${dir}/${diff}/${date}.json`);
  const hasLevel = (entry, diff) => diff === "hard" || !entry || !!entry[diff];

  // ---------- leaderboard API ----------
  const API = ["localhost", "127.0.0.1"].includes(location.hostname) ? "" : (window.METAHUNT_API || "");
  const me = () => { try { return JSON.parse(localStorage.getItem("mh:player")); } catch { return null; } };
  async function api(path, body) {
    const r = await fetch(API + path, body ? { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) } : {});
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`);
    return data;
  }
  function report(kind, puzzleId, answer) {
    const p = me();
    if (!p) return;
    api("/api/" + kind, { token: p.token, date: puzzle.date, difficulty, puzzle: puzzleId, answer })
      .then(() => { if (kind === "solve") renderLeaderboard(); })
      .catch(() => {});
  }

  // ---------- personal timer & sharing ----------
  const hms = (sec) => {
    sec = Math.max(0, Math.round(sec));
    const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
    return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  };
  const b64url = (str) => btoa(unescape(encodeURIComponent(str))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

  function splits(st) {
    // [{id, title, at (s from start), split (s since previous solve), hint}], in solve order.
    if (!st.start) return [];
    const rows = puzzle.puzzles
      .filter((p) => st.times && st.times[p.id])
      .map((p) => ({ id: p.id, title: p.title, at: (st.times[p.id] - st.start) / 1000, hint: st.hints.includes(p.id) }));
    if (st.times && st.times.meta) rows.push({ id: "meta", title: "Meta", at: (st.times.meta - st.start) / 1000, hint: false });
    rows.sort((a, b) => a.at - b.at);
    rows.forEach((r, i) => { r.split = r.at - (i ? rows[i - 1].at : 0); });
    return rows;
  }

  function shareLink(st) {
    const p = me();
    const payload = {
      v: 1, d: puzzle.date, x: difficulty, n: p ? p.name : null,
      s: splits(st).filter((r) => r.id !== "meta").map((r) => [r.id, Math.round(r.at), r.hint ? 1 : 0]),
      m: st.times && st.times.meta && st.start ? Math.round((st.times.meta - st.start) / 1000) : null,
    };
    return new URL("share.html#run=" + b64url(JSON.stringify(payload)), location.href).href;
  }

  function shareText(st) {
    const squares = puzzle.puzzles.map((p) => (st.solved[p.id] ? (st.hints.includes(p.id) ? "🟨" : "🟩") : "⬛")).join("");
    const total = st.times && st.times.meta && st.start ? hms((st.times.meta - st.start) / 1000) : "unfinished";
    const nh = st.hints.length;
    return `Daily Metahunt #${puzzle.number} (${LEVEL[difficulty]}): ${puzzle.round}\n` +
      `⏱ ${total} · ${Object.keys(st.solved).length}/${puzzle.puzzles.length} feeders · ${nh} hint${nh === 1 ? "" : "s"}\n` +
      `${squares}${st.meta ? " ⭐" : ""}\n${shareLink(st)}`;
  }

  // ---------- storage (best-effort) ----------
  const load = (date) => {
    try { return JSON.parse(localStorage.getItem("mh:" + date)) || { solved: {}, hints: [] }; }
    catch { return { solved: {}, hints: [] }; }
  };
  const save = (date, st) => { try { localStorage.setItem("mh:" + date, JSON.stringify(st)); } catch {} };

  // ---------- hashing ----------
  const norm = (s) => s.toUpperCase().replace(/[^A-Z]/g, "");
  async function hash(date, word) {
    const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(`metahunt|${date}|${word}`));
    return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
  }

  // ---------- per-puzzle notes (scratch letters, marks, tiles), kept in this browser ----------
  function notes(c) {
    const k = c && c.key ? "mh:notes:" + c.key : null;
    const read = () => { if (!k) return {}; try { return JSON.parse(localStorage.getItem(k)) || {}; } catch { return {}; } };
    const f = (name) => `${c && c.i != null ? c.i : 0}:${name}`;
    return {
      get: (name, d) => { const v = read()[f(name)]; return v === undefined ? d : v; },
      set: (name, v) => {
        if (!k) return;
        const all = read();
        all[f(name)] = v;
        try { localStorage.setItem(k, JSON.stringify(all)); } catch {}
      },
    };
  }

  // A small box under each item for jotting down what it decodes to.
  function trayWrap(container, nodes, width, c) {
    const s = notes(c);
    const vals = s.get("tray", []);
    const inputs = [];
    nodes.forEach((node, k) => {
      const slot = el("div", "slot");
      const inp = el("input", "slot-in" + (width > 1 ? " wide" : ""));
      inp.maxLength = width;
      if (width > 1) inp.style.width = `calc(${Math.min(width, 14)}ch + 14px)`;
      inp.value = vals[k] || "";
      inp.autocomplete = "off";
      inp.spellcheck = false;
      inp.setAttribute("aria-label", `Your note for item ${k + 1}`);
      inp.addEventListener("input", () => {
        inp.value = inp.value.toUpperCase().replace(/[^A-Z]/g, "").slice(0, width);
        s.set("tray", inputs.map((i) => i.value));
        if (width === 1 && inp.value) inputs[k + 1]?.focus();
      });
      inp.addEventListener("keydown", (e) => {
        if (e.key === "Backspace" && !inp.value && k) { inputs[k - 1].focus(); e.preventDefault(); }
      });
      slot.append(node, inp);
      container.append(slot);
      inputs.push(inp);
    });
    return container;
  }

  // Which blocks get note boxes: 1 = one letter per item, 3 = three letters, "word" = a whole word.
  function trayWidth(b, c) {
    if (!c || b.tray === false) return 0;
    if (b.tray === "word") return 16;
    if (b.tray === "letter") return 1;
    if (["clocks", "semaphore", "flags", "resistors", "pigpen", "braille", "glyphs", "numbers", "taps", "lamp", "tape"].includes(b.type)) return 1;
    if (b.type === "swatches") return 3;
    if (b.type === "mono" && b.big) return 1;
    if (b.type === "list" && !b.tiles && !b.strike) return b.ordered && b.mono ? 16 : 1;
    return 0;
  }

  const sign = (x) => (x > 0) - (x < 0);
  // Cells on the straight line (row, column or diagonal) from a to z, or null.
  function lineCells(a, z) {
    const dr = z[0] - a[0], dc = z[1] - a[1];
    if (dr && dc && Math.abs(dr) !== Math.abs(dc)) return null;
    const n = Math.max(Math.abs(dr), Math.abs(dc));
    return [...Array(n + 1)].map((_, k) => [a[0] + sign(dr) * k, a[1] + sign(dc) * k]);
  }

  // Interactive word search: drag across a word, or click its first and last letters.
  function wordsearch(b, c) {
    const s = notes(c);
    const R = b.rows.length, C = b.rows[0].length;
    const sibling = c && c.blocks && c.blocks[c.i + 1];
    const known = b.words || (sibling && sibling.type === "list" ? sibling.items : null);
    const words = known ? new Set(known) : null;
    let marks = s.get("ws", []);
    let anchor = null, start = null, cur = null, dragging = false, focus = [0, 0];
    const wrap = el("div", "ws-wrap");
    const t = el("table", "board plain ws");
    t.tabIndex = 0;
    t.setAttribute("aria-label", "Word search grid. Drag across a word, or click its first and last letters. Arrow keys move, Enter or Space selects.");
    const cells = b.rows.map((row, r) => {
      const tr = el("tr");
      const out = [...row].map((ch, col) => {
        const td = el("td", null, ch);
        td.dataset.r = r;
        td.dataset.c = col;
        tr.append(td);
        return td;
      });
      t.append(tr);
      return out;
    });
    const status = el("p", "note ws-status");
    status.setAttribute("aria-live", "polite");
    const read = el("p", "ws-read");
    const letters = (line) => line.map(([r, col]) => b.rows[r][col]).join("");
    const same = (m, a, z) => (m[0] === a[0] && m[1] === a[1] && m[2] === z[0] && m[3] === z[1]) || (m[0] === z[0] && m[1] === z[1] && m[2] === a[0] && m[3] === a[1]);
    function paint() {
      const hit = new Set();
      cells.flat().forEach((td) => td.classList.remove("hit", "anchor", "preview", "focus"));
      marks.forEach((m) => lineCells([m[0], m[1]], [m[2], m[3]]).forEach(([r, col]) => { hit.add(r + "," + col); cells[r][col].classList.add("hit"); }));
      if (anchor) cells[anchor[0]][anchor[1]].classList.add("anchor");
      if (dragging && start && cur) (lineCells(start, cur) || [start]).forEach(([r, col]) => cells[r][col].classList.add("preview"));
      if (document.activeElement === t) cells[focus[0]][focus[1]].classList.add("focus");
      let left = "";
      for (let r = 0; r < R; r++) for (let col = 0; col < C; col++) if (!hit.has(r + "," + col)) left += b.rows[r][col];
      read.replaceChildren(el("span", "fitread-label", "Letters not in any marked word:"), el("span", "ws-left", left || "—"));
    }
    function select(a, z) {
      const line = lineCells(a, z);
      if (!line || line.length < 2) { status.textContent = "Words run in a straight line: across, down or diagonally."; return; }
      const i = marks.findIndex((m) => same(m, a, z));
      if (i >= 0) {
        marks.splice(i, 1);
        status.textContent = `Unmarked ${letters(line)}.`;
      } else {
        const w = letters(line), back = [...w].reverse().join("");
        if (words && !words.has(w) && !words.has(back)) { status.textContent = `${w} isn't one of the hidden words.`; return; }
        marks.push([...a, ...z]);
        const found = words ? marks.length : null;
        status.textContent = `Marked ${words && words.has(back) && !words.has(w) ? back : w}.` + (found != null && difficulty !== "hard" ? ` ${found} of ${words.size} found.` : "");
      }
      s.set("ws", marks);
    }
    function tap(pos) {
      if (anchor && (anchor[0] !== pos[0] || anchor[1] !== pos[1])) { select(anchor, pos); anchor = null; }
      else anchor = anchor ? null : pos;
    }
    const posOf = (node) => { const td = node && node.closest ? node.closest("td") : null; return td && t.contains(td) ? [+td.dataset.r, +td.dataset.c] : null; };
    t.addEventListener("pointerdown", (e) => {
      const p = posOf(e.target);
      if (!p) return;
      e.preventDefault();
      t.focus({ preventScroll: true });
      focus = p;
      start = cur = p;
      dragging = true;
      paint();
    });
    window.addEventListener("pointermove", (e) => {
      if (!dragging) return;
      const p = posOf(document.elementFromPoint(e.clientX, e.clientY));
      if (p && (p[0] !== cur[0] || p[1] !== cur[1])) { cur = p; paint(); }
    });
    window.addEventListener("pointerup", () => {
      if (!dragging) return;
      dragging = false;
      if (start[0] === cur[0] && start[1] === cur[1]) tap(start);
      else { select(start, cur); anchor = null; }
      paint();
    });
    t.addEventListener("keydown", (e) => {
      const mv = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] }[e.key];
      if (mv) { focus = [Math.min(R - 1, Math.max(0, focus[0] + mv[0])), Math.min(C - 1, Math.max(0, focus[1] + mv[1]))]; e.preventDefault(); }
      else if (e.key === "Enter" || e.key === " ") { tap(focus); e.preventDefault(); }
      else if (e.key === "Escape") anchor = null;
      else return;
      paint();
    });
    t.addEventListener("focus", paint);
    t.addEventListener("blur", paint);
    const clear = el("button", "btn secondary small", "Clear marks");
    clear.type = "button";
    clear.addEventListener("click", () => { marks = []; anchor = null; s.set("ws", marks); status.textContent = ""; paint(); });
    wrap.append(t, el("p", "note", "Drag across a word, or click its first and last letters. Select a marked word again to unmark it."), status, read, clear);
    paint();
    return wrap;
  }

  // Word list chips you can strike through (older word searches print their list).
  function strikeList(b, c) {
    const s = notes(c);
    const struck = new Set(s.get("strike", []));
    const box = el("div", "chips");
    b.items.forEach((w) => {
      const chip = el("button", "chip strike" + (struck.has(w) ? " struck" : ""), w);
      chip.type = "button";
      chip.setAttribute("aria-pressed", struck.has(w));
      chip.addEventListener("click", () => {
        struck.has(w) ? struck.delete(w) : struck.add(w);
        chip.classList.toggle("struck", struck.has(w));
        chip.setAttribute("aria-pressed", struck.has(w));
        s.set("strike", [...struck]);
      });
      box.append(chip);
    });
    return box;
  }

  // Shredded sentence: click strips to lay them out in order.
  function tiles(b, c) {
    const s = notes(c);
    let order = s.get("tiles", []).filter((i) => i < b.items.length);
    const sibling = c && c.blocks && c.blocks[c.i + 1];
    const m = sibling && sibling.text && sibling.text.match(/\(([\d ]+)\)/);
    const lengths = m ? m[1].trim().split(/\s+/).map(Number) : [];
    const wrap = el("div", "tiles");
    const pool = el("div", "chips");
    const laid = el("div", "chips tiles-laid");
    const reads = el("p", "ws-read");
    function paint() {
      pool.replaceChildren();
      laid.replaceChildren();
      b.items.forEach((t, i) => {
        const chip = el("button", "chip tile", t);
        chip.type = "button";
        chip.disabled = order.includes(i);
        chip.addEventListener("click", () => { order.push(i); s.set("tiles", order); paint(); });
        pool.append(chip);
      });
      order.forEach((i, k) => {
        const chip = el("button", "chip tile laid", b.items[i]);
        chip.type = "button";
        chip.title = "Put back";
        chip.addEventListener("click", () => { order.splice(k, 1); s.set("tiles", order); paint(); });
        laid.append(chip);
      });
      if (!order.length) laid.append(el("span", "note", "Click strips above to lay them out here; click a laid strip to put it back."));
      let flat = order.map((i) => b.items[i]).join(""), words = [];
      for (const n of lengths) { if (!flat) break; words.push(flat.slice(0, n)); flat = flat.slice(n); }
      if (flat) words.push(flat);
      reads.replaceChildren(el("span", "fitread-label", "Reads:"), el("span", "ws-left", words.join(" ") || "—"));
    }
    const clear = el("button", "btn secondary small", "Start again");
    clear.type = "button";
    clear.addEventListener("click", () => { order = []; s.set("tiles", order); paint(); });
    wrap.append(pool, laid, reads, clear);
    paint();
    return wrap;
  }

  // Substitution solver: type a letter under a symbol and every copy of it fills in.
  function substitution(b, c) {
    const s = notes(c);
    const map = s.get("sub", {});
    const wrap = el("div", "subst");
    if (b.wheel) wrap.append(wheel(b.text));
    const box = el("div", "subst-text");
    const all = [];
    const refresh = () => {
      const count = {};
      Object.values(map).forEach((v) => { if (v) count[v] = (count[v] || 0) + 1; });
      all.forEach(({ sym, inp }) => { inp.value = map[sym] || ""; inp.classList.toggle("dup", !!inp.value && count[inp.value] > 1); });
    };
    b.text.split(" ").forEach((w) => {
      const word = el("span", "subst-word");
      [...w].forEach((sym) => {
        const cell = el("span", "subst-cell");
        const inp = el("input", "subst-in");
        inp.maxLength = 1;
        inp.autocomplete = "off";
        inp.spellcheck = false;
        inp.setAttribute("aria-label", `Letter for ${sym}`);
        const k = all.length;
        inp.addEventListener("input", () => {
          map[sym] = inp.value.toUpperCase().replace(/[^A-Z]/g, "").slice(-1);
          s.set("sub", map);
          refresh();
          if (map[sym]) all.slice(k + 1).find((x) => !x.inp.value)?.inp.focus();
        });
        inp.addEventListener("focus", () => all.forEach((x) => x.cell.classList.toggle("same", x.sym === sym)));
        cell.append(el("span", "subst-sym", sym), inp);
        word.append(cell);
        all.push({ sym, inp, cell });
      });
      box.append(word);
    });
    box.addEventListener("focusout", () => setTimeout(() => { if (!box.contains(document.activeElement)) all.forEach((x) => x.cell.classList.remove("same")); }));
    const clear = el("button", "btn secondary small", "Clear letters");
    clear.type = "button";
    clear.addEventListener("click", () => { Object.keys(map).forEach((k) => delete map[k]); s.set("sub", map); refresh(); });
    wrap.append(el("p", "note", "Type a letter under any symbol and every copy of that symbol fills in. Letters used twice turn red."), box, clear);
    refresh();
    return wrap;
  }

  // A cipher wheel for the easy shift puzzles.
  function wheel(text) {
    const box = el("div", "wheel");
    let k = 0;
    const out = el("pre", "mono wide");
    const label = el("span", "wheel-k");
    const show = () => {
      label.textContent = `Shift back by ${k}`;
      out.textContent = [...text].map((ch) => (/[A-Z]/.test(ch) ? String.fromCharCode((ch.charCodeAt(0) - 65 - k + 26) % 26 + 65) : ch)).join("");
    };
    const btn = (t, d) => {
      const x = el("button", "btn secondary small", t);
      x.type = "button";
      x.setAttribute("aria-label", d > 0 ? "Turn the wheel forward" : "Turn the wheel back");
      x.addEventListener("click", () => { k = (k + d + 26) % 26; show(); });
      return x;
    };
    const row = el("div", "wheel-row");
    row.append(btn("◀", -1), label, btn("▶", 1));
    box.append(row, out);
    show();
    return box;
  }

  // ---------- block renderers ----------
  const RESISTOR = { black: "#161616", brown: "#7a4a24", red: "#c9302c", orange: "#e8812a", yellow: "#f2cf2a", green: "#3f9b4a", blue: "#2f67c9", violet: "#8a4fc7", grey: "#8c8c8c", white: "#f4f4f4", gold: "#c9a227" };

  function clock(pair) {
    const s = svg("svg", { width: 84, height: 84, viewBox: "-42 -42 84 84", role: "img", "aria-label": "clock" });
    s.append(svg("circle", { r: 38, fill: "var(--paper)", stroke: "var(--line)", "stroke-width": 2 }));
    for (let i = 0; i < 12; i++) {
      const a = (i * Math.PI) / 6, big = i % 3 === 0;
      s.append(svg("line", { x1: Math.sin(a) * (big ? 29 : 32), y1: -Math.cos(a) * (big ? 29 : 32), x2: Math.sin(a) * 35, y2: -Math.cos(a) * 35, stroke: "#2b2418", "stroke-width": big ? 2.5 : 1.2 }));
    }
    pair.forEach((d, i) => {
      const a = (d * Math.PI) / 4, len = i === 0 ? 30 : 21;
      s.append(svg("line", { x1: 0, y1: 0, x2: Math.sin(a) * len, y2: -Math.cos(a) * len, stroke: "#2b2418", "stroke-width": i === 0 ? 2.5 : 4, "stroke-linecap": "round" }));
    });
    s.append(svg("circle", { r: 3, fill: "#2b2418" }));
    return s;
  }

  function resistor(bands) {
    const s = svg("svg", { width: 150, height: 44, viewBox: "0 0 150 44", role: "img", "aria-label": "resistor" });
    s.append(svg("line", { x1: 0, y1: 22, x2: 150, y2: 22, stroke: "#9a9a9a", "stroke-width": 3 }));
    s.append(svg("rect", { x: 28, y: 6, width: 94, height: 32, rx: 14, fill: "#d8c39a", stroke: "#8e7a52" }));
    const xs = [42, 58, 74, 104];
    bands.forEach((b, i) => s.append(svg("rect", { x: xs[i], y: 6, width: 8, height: 32, fill: RESISTOR[b] })));
    return s;
  }

  function pigpen(it) {
    const s = svg("svg", { width: 44, height: 44, viewBox: "0 0 44 44", role: "img", "aria-label": "glyph" });
    const st = { stroke: "var(--ink)", "stroke-width": 3, fill: "none", "stroke-linecap": "round", "stroke-linejoin": "round" };
    const m = 6, M = 38, c = 22;
    let dot = [c, c];
    if (it.g === "hash") {
      const r = Math.floor(it.p / 3), col = it.p % 3;
      if (r > 0) s.append(svg("line", { x1: m, y1: m, x2: M, y2: m, ...st }));
      if (r < 2) s.append(svg("line", { x1: m, y1: M, x2: M, y2: M, ...st }));
      if (col > 0) s.append(svg("line", { x1: m, y1: m, x2: m, y2: M, ...st }));
      if (col < 2) s.append(svg("line", { x1: M, y1: m, x2: M, y2: M, ...st }));
    } else {
      // 0 = top wedge (V), 1 = left (>), 2 = right (<), 3 = bottom (Λ)
      const pts = [
        [[m, m], [c, M - 4], [M, m]],
        [[m, m], [M - 4, c], [m, M]],
        [[M, m], [m + 4, c], [M, M]],
        [[m, M], [c, m + 4], [M, M]],
      ][it.p];
      s.append(svg("polyline", { points: pts.map((p) => p.join(",")).join(" "), ...st }));
      dot = [[c, m + 9], [m + 8, c], [M - 8, c], [c, M - 9]][it.p];
    }
    if (it.dot) s.append(svg("circle", { cx: dot[0], cy: dot[1], r: 3.2, fill: "var(--ink)" }));
    return s;
  }

  // International maritime signal flags, drawn on a 60×40 field.
  const FC = { r: "#d42a2a", b: "#1d3f9a", y: "#f4c20d", w: "#ffffff", k: "#161616" };
  const rect = (x, y, w, h, f) => svg("rect", { x, y, width: w, height: h, fill: FC[f] });
  const poly = (pts, f) => svg("polygon", { points: pts, fill: FC[f] });
  const FLAGS = {
    A: () => [rect(0, 0, 30, 40, "w"), poly("30,0 60,0 45,20 60,40 30,40", "b")],
    B: () => [poly("0,0 60,0 45,20 60,40 0,40", "r")],
    C: () => ["b", "w", "r", "w", "b"].map((f, i) => rect(0, i * 8, 60, 8, f)),
    D: () => [rect(0, 0, 60, 40, "y"), rect(0, 10, 60, 20, "b")],
    E: () => [rect(0, 0, 60, 20, "b"), rect(0, 20, 60, 20, "r")],
    F: () => [rect(0, 0, 60, 40, "w"), poly("30,0 60,20 30,40 0,20", "r")],
    G: () => [0, 1, 2, 3, 4, 5].map((i) => rect(i * 10, 0, 10, 40, i % 2 ? "b" : "y")),
    H: () => [rect(0, 0, 30, 40, "w"), rect(30, 0, 30, 40, "r")],
    I: () => [rect(0, 0, 60, 40, "y"), svg("circle", { cx: 30, cy: 20, r: 10, fill: FC.k })],
    J: () => [rect(0, 0, 60, 40, "b"), rect(0, 13.3, 60, 13.4, "w")],
    K: () => [rect(0, 0, 30, 40, "y"), rect(30, 0, 30, 40, "b")],
    L: () => [rect(0, 0, 60, 40, "y"), rect(30, 0, 30, 20, "k"), rect(0, 20, 30, 20, "k")],
    M: () => [rect(0, 0, 60, 40, "b"), poly("0,0 8,0 60,34 60,40 52,40 0,6", "w"), poly("60,0 52,0 0,34 0,40 8,40 60,6", "w")],
    N: () => [...Array(16)].map((_, i) => rect((i % 4) * 15, Math.floor(i / 4) * 10, 15, 10, (i % 4 + Math.floor(i / 4)) % 2 ? "w" : "b")),
    O: () => [rect(0, 0, 60, 40, "y"), poly("0,0 60,0 0,40", "r")],
    P: () => [rect(0, 0, 60, 40, "b"), rect(20, 12, 20, 16, "w")],
    Q: () => [rect(0, 0, 60, 40, "y")],
    R: () => [rect(0, 0, 60, 40, "r"), rect(26, 0, 8, 40, "y"), rect(0, 16, 60, 8, "y")],
    S: () => [rect(0, 0, 60, 40, "w"), rect(20, 12, 20, 16, "b")],
    T: () => [rect(0, 0, 20, 40, "r"), rect(20, 0, 20, 40, "w"), rect(40, 0, 20, 40, "b")],
    U: () => [rect(0, 0, 60, 40, "w"), rect(0, 0, 30, 20, "r"), rect(30, 20, 30, 20, "r")],
    V: () => [rect(0, 0, 60, 40, "w"), poly("0,0 8,0 60,34 60,40 52,40 0,6", "r"), poly("60,0 52,0 0,34 0,40 8,40 60,6", "r")],
    W: () => [rect(0, 0, 60, 40, "b"), rect(9, 6, 42, 28, "w"), rect(19, 13, 22, 14, "r")],
    X: () => [rect(0, 0, 60, 40, "w"), rect(26, 0, 8, 40, "b"), rect(0, 16, 60, 8, "b")],
    Y: () => [rect(0, 0, 60, 40, "y"), ...[-40, -20, 0, 20, 40].map((o) => poly(`${o},0 ${o + 10},0 ${o + 50},40 ${o + 40},40`, "r"))],
    Z: () => [poly("0,0 60,0 30,20", "y"), poly("60,0 60,40 30,20", "b"), poly("0,40 60,40 30,20", "r"), poly("0,0 0,40 30,20", "k")],
  };
  function flag(ch) {
    const s = svg("svg", { width: 72, height: 48, viewBox: "0 0 60 40", role: "img", "aria-label": "flag" });
    const clip = "c" + Math.random().toString(36).slice(2);
    const cp = svg("clipPath", { id: clip });
    cp.append(svg("rect", { width: 60, height: 40 }));
    const g = svg("g", { "clip-path": `url(#${clip})` });
    FLAGS[ch]().forEach((e) => g.append(e));
    s.append(cp, g, svg("rect", { width: 60, height: 40, fill: "none", stroke: "rgba(0,0,0,.35)", "stroke-width": 0.8 }));
    return s;
  }

  function board(b, c) {
    if (b.plain) return wordsearch(b, c);
    const s = notes(c);
    let path = s.get("path", []);
    const t = el("table", "board chess");
    const files = "abcdefgh";
    const tds = {};
    const read = el("p", "ws-read");
    const paint = () => {
      Object.values(tds).forEach((td) => { td.classList.remove("visited"); td.querySelector(".cellnum")?.remove(); });
      path.forEach((sq, k) => { const td = tds[sq]; td.classList.add("visited"); td.append(el("span", "cellnum", String(k + 1))); });
      read.replaceChildren(el("span", "fitread-label", "Squares you've marked:"), el("span", "ws-left", path.map((sq) => tds[sq].firstChild.textContent).join("") || "—"));
    };
    b.rows.forEach((row, r) => {
      const tr = el("tr");
      tr.append(el("th", null, String(8 - r)));
      [...row].forEach((ch, col) => {
        const sq = files[col] + (8 - r);
        const td = el("td", (r + col) % 2 ? "dark" : null);
        td.append(document.createTextNode(ch));
        td.tabIndex = 0;
        td.setAttribute("aria-label", `${sq}: ${ch}`);
        const toggle = () => {
          const i = path.indexOf(sq);
          if (i >= 0) path.splice(i, 1); else path.push(sq);
          s.set("path", path);
          paint();
        };
        td.addEventListener("click", toggle);
        td.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { toggle(); e.preventDefault(); } });
        tds[sq] = td;
        tr.append(td);
      });
      t.append(tr);
    });
    const tr = el("tr");
    tr.append(el("th"));
    [...files].forEach((f) => tr.append(el("th", null, f)));
    t.append(tr);
    const wrap = el("div");
    const clear = el("button", "btn secondary small", "Clear marks");
    clear.type = "button";
    clear.addEventListener("click", () => { path = []; s.set("path", path); paint(); });
    wrap.append(t, el("p", "note", "Click squares to mark them in order; click again to unmark."), read, clear);
    paint();
    return wrap;
  }

  // Interactive nonogram: click cycles empty → filled → crossed.
  function nonogram(b) {
    const R = b.rows.length, C = b.cols.length;
    const given = {};
    b.givens.forEach(([r, c, v]) => { given[r + "," + c] = v; });
    const wrap = el("div", "nono-wrap");
    const t = el("table", "nono");
    const head = el("tr");
    head.append(el("th", "corner"));
    b.cols.forEach((clue) => {
      const th = el("th", "colclue");
      (clue.length ? clue : [0]).forEach((n) => th.append(el("div", null, String(n))));
      head.append(th);
    });
    t.append(head);
    for (let r = 0; r < R; r++) {
      const tr = el("tr");
      tr.append(el("th", "rowclue", (b.rows[r].length ? b.rows[r] : [0]).join(" ")));
      for (let c = 0; c < C; c++) {
        const td = el("td", "cell");
        const g = given[r + "," + c];
        if (g !== undefined) {
          td.classList.add(g ? "filled" : "crossed", "given");
        } else {
          td.addEventListener("click", () => {
            if (td.classList.contains("filled")) { td.classList.replace("filled", "crossed"); }
            else if (td.classList.contains("crossed")) { td.classList.remove("crossed"); }
            else { td.classList.add("filled"); }
          });
        }
        tr.append(td);
      }
      t.append(tr);
    }
    wrap.append(t);
    // Size the squares so the whole grid fits the card without sideways scrolling.
    const fit = () => {
      const avail = wrap.clientWidth;
      if (!avail) return;
      const clue = t.querySelector(".rowclue");
      t.style.setProperty("--cell", "20px");
      const clueW = clue ? clue.offsetWidth : 60;
      const size = Math.floor((avail - clueW - 4) / C);
      t.style.setProperty("--cell", Math.max(12, Math.min(28, size)) + "px");
    };
    if (window.ResizeObserver) new ResizeObserver(fit).observe(wrap);
    requestAnimationFrame(fit);
    const legend = el("p", "note nono-legend");
    legend.innerHTML = '<span class="nono-key filled"></span> filled &nbsp; <span class="nono-key crossed">×</span> empty &nbsp; ' +
      '<span class="nono-key given"></span> given &nbsp;·&nbsp; click to cycle blank → filled → ×';
    wrap.append(legend);
    return wrap;
  }

  // Letter-box helpers shared by the fill-in grids: type to advance, backspace to go back.
  function letterInput(cls, label, onChange, next, prev) {
    const inp = el("input", cls);
    inp.maxLength = 1;
    inp.autocomplete = "off";
    inp.spellcheck = false;
    inp.setAttribute("aria-label", label);
    inp.addEventListener("input", () => {
      inp.value = inp.value.toUpperCase().replace(/[^A-Z]/g, "").slice(-1);
      onChange();
      if (inp.value) next()?.focus();
    });
    inp.addEventListener("keydown", (e) => {
      if (e.key === "Backspace" && !inp.value) { const p = prev(); if (p) { p.focus(); p.value = ""; onChange(); e.preventDefault(); } }
      if (e.key === "ArrowRight") next()?.focus();
      if (e.key === "ArrowLeft") prev()?.focus();
    });
    return inp;
  }

  function fitgrid(b) {
    const g = el("div", "fitgrid");
    g.append(el("p", "note", "Every answer fits exactly one row. Solved answers drop in automatically; you can also type."));
    const readBox = el("p", "fitread");
    const update = () => {
      readBox.replaceChildren(el("span", "fitread-label", "Shaded squares, top to bottom:"));
      g.querySelectorAll(".fitrow").forEach((row) => {
        const v = row.querySelector(".shade").value;
        readBox.append(el("span", "fitread-letter" + (v ? "" : " empty"), v || "·"));
      });
    };
    b.rows.forEach((row, r) => {
      const line = el("div", "fitrow");
      line.dataset.len = row.len;
      line.append(el("span", "fitlen", String(row.len)));
      const cells = el("div", "fitcells");
      const inputs = [];
      for (let i = 0; i < row.len; i++) {
        const inp = letterInput("fitcell" + (i === row.shade ? " shade" : ""), `row ${r + 1}, letter ${i + 1}`,
          () => { delete line.dataset.from; line.querySelector(".fitsrc").textContent = ""; update(); },
          () => inputs[i + 1], () => inputs[i - 1]);
        inputs.push(inp);
        cells.append(inp);
      }
      line.append(cells, el("span", "fitsrc"));
      g.append(line);
    });
    g.append(readBox);
    update();
    g._update = update;
    return g;
  }

  // Drop every solved answer into the fit-in row of the same length.
  function fillFitgrid() {
    const g = document.querySelector("#meta .fitgrid");
    if (!g) return;
    const st = load(rk());
    Object.entries(st.solved).forEach(([id, word]) => {
      const row = g.querySelector(`.fitrow[data-len="${word.length}"]`);
      if (!row || (row.dataset.from && row.dataset.from !== id)) return;
      row.querySelectorAll("input").forEach((inp, i) => { inp.value = word[i]; });
      row.dataset.from = id;
      row.classList.add("filled");
      row.querySelector(".fitsrc").textContent = `puzzle ${id}`;
    });
    g._update();
  }

  function sudoku(b) {
    const n = b.size, [br, bc] = n === 6 ? [2, 3] : [3, 3];
    const marks = {};
    b.marks.forEach(([r, c], i) => { marks[r + "," + c] = i + 1; });
    const wrap = el("div");
    wrap.append(el("p", "note", "Letters: " + [...b.alphabet].join(" ")));
    const t = el("table", "sudoku");
    b.rows.forEach((row, r) => {
      const tr = el("tr");
      [...row].forEach((ch, c) => {
        const td = el("td");
        if ((c + 1) % bc === 0 && c < n - 1) td.classList.add("box-r");
        if ((r + 1) % br === 0 && r < n - 1) td.classList.add("box-b");
        if (ch !== ".") { td.textContent = ch; td.classList.add("given"); }
        else {
          const inp = el("input");
          inp.maxLength = 1;
          inp.setAttribute("aria-label", `row ${r + 1} column ${c + 1}`);
          inp.addEventListener("input", () => { inp.value = inp.value.toUpperCase().replace(/[^A-Z]/g, ""); });
          td.append(inp);
        }
        const m = marks[r + "," + c];
        if (m) { td.classList.add("marked"); td.append(el("span", "cellnum", String(m))); }
        tr.append(td);
      });
      t.append(tr);
    });
    wrap.append(t);
    return wrap;
  }

  function dropquote(b) {
    const W = b.cols.length;
    const wrap = el("div");
    wrap.append(el("p", "note", "Each column's letters drop into the open squares directly below them, in some order. Hatched squares are the gaps between words."));
    const t = el("table", "dropquote");
    const depth = Math.max(...b.cols.map((c) => c.length));
    const pool = b.cols.map(() => []);
    for (let r = 0; r < depth; r++) {
      const tr = el("tr", "pool");
      b.cols.forEach((col, c) => {
        const pad = depth - col.length;
        const td = el("td", null, r >= pad ? col[r - pad] : "");
        td.dataset.col = c;
        if (r >= pad) pool[c].push(td);
        tr.append(td);
      });
      t.append(tr);
    }
    const slots = [];
    const recount = () => {
      pool.forEach((tds) => tds.forEach((td) => td.classList.remove("used")));
      slots.forEach((inp) => {
        inp.classList.remove("bad");
        if (!inp.value) return;
        const free = pool[inp.dataset.col].find((td) => td.textContent === inp.value && !td.classList.contains("used"));
        if (free) free.classList.add("used");
        else inp.classList.add("bad");  // that letter isn't available in this column
      });
    };
    const focusCol = (c) => t.querySelectorAll("td").forEach((td) => td.classList.toggle("col-focus", td.dataset.col === String(c)));
    b.mask.forEach((row) => {
      const tr = el("tr", "slots");
      [...row].forEach((m, c) => {
        const td = el("td", m === "#" ? "black" : "open");
        td.dataset.col = c;
        if (m !== "#") {
          const k = slots.length;
          const inp = letterInput("", `column ${c + 1}`, recount, () => slots[k + 1], () => slots[k - 1]);
          inp.dataset.col = c;
          inp.addEventListener("focus", () => focusCol(c));
          slots.push(inp);
          td.append(inp);
        }
        tr.append(td);
      });
      t.append(tr);
    });
    t.addEventListener("focusout", () => setTimeout(() => { if (!t.contains(document.activeElement)) focusCol(-1); }));
    const scroll = el("div", "scroll-x");
    scroll.append(t);
    wrap.append(scroll);
    return wrap;
  }

  function lamp(b) {
    const box = el("div", "lamp");
    b.groups.forEach((g) => {
      const row = el("div", "lamp-row");
      [...g].forEach((s) => row.append(el("span", s === "." ? "flash short" : "flash long")));
      box.append(row);
    });
    return box;
  }

  function braille(b) {
    const g = el("div", "gallery");
    b.items.forEach((bits) => {
      const cell = el("div", "braille-cell");
      [0, 3, 1, 4, 2, 5].forEach((k) => cell.append(el("span", bits[k] === "1" ? "dot on" : "dot")));
      g.append(cell);
    });
    return g;
  }

  function semaphoreFigure(pair) {
    const s = svg("svg", { width: 70, height: 84, viewBox: "-35 -40 70 84", role: "img", "aria-label": "signaller" });
    const st = { stroke: "var(--ink)", "stroke-width": 3, "stroke-linecap": "round" };
    s.append(svg("circle", { cx: 0, cy: -22, r: 6, fill: "none", ...st }));
    s.append(svg("line", { x1: 0, y1: -16, x2: 0, y2: 14, ...st }));
    s.append(svg("line", { x1: 0, y1: 14, x2: -8, y2: 38, ...st }));
    s.append(svg("line", { x1: 0, y1: 14, x2: 8, y2: 38, ...st }));
    pair.forEach((d) => {
      const a = (d * Math.PI) / 4, x = Math.sin(a) * 26, y = -8 - Math.cos(a) * 26;
      s.append(svg("line", { x1: 0, y1: -8, x2: x, y2: y, ...st }));
      s.append(svg("rect", { x: x - 5, y: y - 5, width: 10, height: 10, fill: "#d42a2a", stroke: "#f4c20d", "stroke-width": 1.5 }));
    });
    return s;
  }

  // Audio puzzles are synthesised in the browser, so there are no files to peek at.
  let audioCtx = null;
  function playAudio(b, btn) {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    const ctx = audioCtx, t0 = ctx.currentTime + 0.1;
    let t = t0;
    const tone = (freqs, start, dur) => {
      freqs.forEach((f) => {
        const o = ctx.createOscillator(), g = ctx.createGain();
        o.frequency.value = f;
        o.type = b.kind === "taps" ? "triangle" : "sine";
        g.gain.setValueAtTime(0, start);
        g.gain.linearRampToValueAtTime(0.18 / freqs.length, start + 0.005);
        g.gain.setValueAtTime(0.18 / freqs.length, start + dur - 0.01);
        g.gain.linearRampToValueAtTime(0, start + dur);
        o.connect(g).connect(ctx.destination);
        o.start(start);
        o.stop(start + dur + 0.02);
      });
    };
    const DTMF = { 1: [697, 1209], 2: [697, 1336], 3: [697, 1477], 4: [770, 1209], 5: [770, 1336], 6: [770, 1477], 7: [852, 1209], 8: [852, 1336], 9: [852, 1477] };
    if (b.kind === "morse") {
      const u = 0.09;
      b.groups.forEach((g) => {
        [...g].forEach((s) => { const d = s === "." ? u : 3 * u; tone([640], t, d); t += d + u; });
        t += 2 * u;
      });
    } else if (b.kind === "dtmf") {
      b.groups.forEach((g) => {
        [...g].forEach((k) => { tone(DTMF[k], t, 0.13); t += 0.2; });
        t += 0.55;
      });
    } else {
      b.groups.forEach(([a, c]) => {
        for (let i = 0; i < a; i++) { tone([180], t, 0.05); t += 0.2; }
        t += 0.45;
        for (let i = 0; i < c; i++) { tone([180], t, 0.05); t += 0.2; }
        t += 1.0;
      });
    }
    btn.disabled = true;
    btn.textContent = "Playing…";
    setTimeout(() => { btn.disabled = false; btn.textContent = "▶ Play again"; }, (t - t0 + 0.3) * 1000);
  }

  function audio(b) {
    const btn = el("button", "btn secondary audio-btn", "▶ Play");
    btn.type = "button";
    btn.addEventListener("click", () => playAudio(b, btn));
    return btn;
  }

  // Items drawn one per letter, so each can carry a note box.
  function itemNodes(b) {
    switch (b.type) {
      case "clocks": return b.items.map(clock);
      case "semaphore": return b.items.map(semaphoreFigure);
      case "flags": return b.items.map(flag);
      case "resistors": return b.items.map(resistor);
      case "pigpen": return b.items.map(pigpen);
      case "numbers": return b.items.map((n) => el("span", "chip", String(n)));
      case "glyphs": return b.groups.map((g) => el("span", "chip glyph", g));
      case "taps": return b.groups.map(([a, c]) => { const x = el("span", "chip"); x.append(a, el("span", "gap"), c); return x; });
      case "mono": return [...b.text].map((ch) => el("span", "bigchar", ch));
      case "list": return b.items.map((t) => el("span", "chip", t));
      default: return null;
    }
  }

  function renderBlock(b, c) {
    const width = trayWidth(b, c);
    if (width && b.type === "list" && !b.inline) {
      const l = el(b.ordered ? "ol" : "ul", "plain-list tray-list" + (b.mono ? " mono-list" : ""));
      const vals = notes(c).get("tray", []);
      const inputs = [];
      b.items.forEach((t, k) => {
        const li = el("li");
        const inp = el("input", "slot-in" + (width > 1 ? " wide" : ""));
        inp.maxLength = width;
        inp.value = vals[k] || "";
        inp.autocomplete = "off";
        inp.spellcheck = false;
        inp.setAttribute("aria-label", `Your note for line ${k + 1}`);
        inp.addEventListener("input", () => {
          inp.value = inp.value.toUpperCase().replace(/[^A-Z]/g, "").slice(0, width);
          notes(c).set("tray", inputs.map((i) => i.value));
          if (width === 1 && inp.value) inputs[k + 1]?.focus();
        });
        inputs.push(inp);
        li.append(el("span", "tray-text", t), inp);
        l.append(li);
      });
      return l;
    }
    if (width && ["lamp", "tape", "braille", "swatches"].includes(b.type)) {
      const node = renderBlock(b, null);
      const rows = [...node.children];
      node.replaceChildren();
      node.classList.add(b.type === "lamp" || b.type === "tape" ? "tray-rows" : "tray-gallery");
      return trayWrap(node, rows, width, c);
    }
    if (width) {
      const nodes = itemNodes(b);
      if (nodes) return trayWrap(el("div", "gallery tray-gallery" + (b.type === "mono" ? " bigchars" : "")), nodes, width, c);
    }
    switch (b.type) {
      case "mono":
        if (b.solver === "substitution" && c) return substitution(b, c);
        return el("pre", "mono" + (b.big ? " big" : "") + (b.wide ? " wide" : ""), b.text);
      case "prose": return el("p", "prose", b.text);
      case "caption": return el("p", "caption", b.text);
      case "board": return board(b, c);
      case "nonogram": return nonogram(b);
      case "fitgrid": return fitgrid(b);
      case "sudoku": return sudoku(b);
      case "dropquote": return dropquote(b);
      case "lamp": return lamp(b);
      case "braille": return braille(b);
      case "audio": return audio(b);
      case "semaphore": {
        const g = el("div", "gallery");
        b.items.forEach((p) => g.append(semaphoreFigure(p)));
        return g;
      }
      case "flags": {
        const g = el("div", "gallery");
        b.items.forEach((ch) => g.append(flag(ch)));
        return g;
      }
      case "numbers": {
        const ul = el("ul", "chips");
        b.items.forEach((n) => ul.append(el("li", "chip", String(n))));
        return ul;
      }
      case "glyphs": {
        const ul = el("ul", "chips");
        b.groups.forEach((g) => ul.append(el("li", "chip glyph", g)));
        return ul;
      }
      case "taps": {
        const ul = el("ul", "chips taps");
        b.groups.forEach(([a, c]) => {
          const li = el("li", "chip");
          li.append(a, el("span", "gap"), c);
          ul.append(li);
        });
        return ul;
      }
      case "list": {
        if (b.tiles && c) return tiles(b, c);
        if (b.strike && c) return strikeList(b, c);
        if (b.inline) {
          const ul = el("ul", "chips");
          b.items.forEach((t) => ul.append(el("li", "chip", t)));
          return ul;
        }
        const l = el(b.ordered ? "ol" : "ul", "plain-list" + (b.mono ? " mono-list" : ""));
        b.items.forEach((t) => l.append(el("li", null, t)));
        return l;
      }
      case "clocks": {
        const g = el("div", "gallery");
        b.items.forEach((p) => g.append(clock(p)));
        return g;
      }
      case "resistors": {
        const g = el("div", "gallery");
        b.items.forEach((p) => g.append(resistor(p)));
        return g;
      }
      case "pigpen": {
        const g = el("div", "gallery");
        b.items.forEach((p) => g.append(pigpen(p)));
        return g;
      }
      case "swatches": {
        const g = el("div", "gallery");
        b.items.forEach((h) => {
          const w = el("div", "swatch");
          const c = el("div", "chip-color");
          c.style.background = h;
          w.append(c, el("div", "code", h));
          g.append(w);
        });
        return g;
      }
      case "tape": {
        const t = el("div", "tape");
        b.rows.forEach((row) => {
          const r = el("div", "tape-row");
          row.forEach((bit, i) => {
            if (i === 3) r.append(el("span", "sprocket"));
            r.append(el("span", "hole " + (bit ? "on" : "off")));
          });
          t.append(r);
        });
        return t;
      }
      default: return el("pre", "mono", JSON.stringify(b));
    }
  }

  // ---------- answer boxes ----------
  function answerForm(onSubmit, placeholder) {
    const form = el("form", "answer");
    const input = el("input");
    input.placeholder = placeholder || "Your answer";
    input.autocomplete = "off";
    input.spellcheck = false;
    input.setAttribute("aria-label", placeholder || "Answer");
    const btn = el("button", "btn", "Check");
    btn.type = "submit";
    const fb = el("div", "feedback");
    fb.setAttribute("aria-live", "polite");
    form.append(input, btn);
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const v = norm(input.value);
      if (v) onSubmit(v, fb, input);
    });
    const wrap = el("div");
    wrap.append(form, fb);
    return wrap;
  }

  // Hints come in tiers: each click reveals the next, stronger one. Only the first costs a penalty.
  function hintBox(id, list, st) {
    const box = el("div", "hints");
    st.hintTiers = st.hintTiers || {};
    let shown = st.hintTiers[id] || (st.hints.includes(id) ? 1 : 0);
    const btn = el("button", "btn secondary", "Hint");
    btn.type = "button";
    const paint = () => {
      box.querySelectorAll(".hint").forEach((h) => h.remove());
      list.slice(0, shown).forEach((h, k) => box.insertBefore(el("div", "hint", list.length > 1 ? `Hint ${k + 1}: ${h}` : h), btn));
      btn.textContent = shown ? `Stronger hint (${shown + 1} of ${list.length})` : list.length > 1 ? `Hint (1 of ${list.length})` : "Hint";
      btn.hidden = shown >= list.length;
    };
    btn.addEventListener("click", () => {
      if (!shown) {
        const penalty = me() ? " On the leaderboard it adds a 5-minute penalty (once per puzzle)." : "";
        if (!confirm("Reveal a hint for this puzzle? It will be noted on your record." + penalty)) return;
      } else if (!confirm("Reveal a stronger hint? It gives away more than the last one.")) return;
      shown++;
      st.hintTiers[id] = shown;
      const first = !st.hints.includes(id);
      if (first) st.hints.push(id);
      save(rk(), st);
      paint();
      if (first) {
        updateProgress();
        renderLiveSplits();
        report("hint", id);
      }
    });
    box.append(btn);
    paint();
    return box;
  }

  // Older rounds printed some interactive pieces as plain lists; give them the new controls.
  function upgradeBlocks(blocks) {
    return blocks.map((b, i) => {
      const next = blocks[i + 1], prev = blocks[i - 1];
      if (b.type === "list" && b.inline && !b.tiles && next && next.type === "prose" && /^Word lengths:/.test(next.text)) return { ...b, tiles: true };
      if (b.type === "list" && b.inline && prev && prev.type === "board" && prev.plain) return { ...b, strike: true };
      if (b.type === "mono" && b.wide && !b.rails && !b.solver) return { ...b, solver: "substitution" };
      return b;
    });
  }

  function scratchpad(key) {
    const d = el("details", "scratch");
    d.append(el("summary", null, "Notes"));
    const ta = el("textarea");
    ta.rows = 4;
    ta.spellcheck = false;
    ta.setAttribute("aria-label", "Your notes");
    ta.placeholder = "Working space. Saved in this browser.";
    const k = "mh:scratch:" + key;
    try { ta.value = localStorage.getItem(k) || ""; } catch {}
    if (ta.value) d.open = true;
    ta.addEventListener("input", () => { try { localStorage.setItem(k, ta.value); } catch {} });
    d.append(ta);
    return d;
  }

  function renderPuzzle(p, st) {
    const card = el("article", "card");
    card.id = "p" + p.id;
    const head = el("div", "card-head");
    head.append(el("span", "num", "PUZZLE " + String(p.id).padStart(2, "0")));
    const h2 = el("h2", null, p.title);
    if (p.length) h2.append(el("span", "enum", ` (${p.length})`));
    card.append(head, h2);
    if (p.technique) card.append(el("span", "technique", p.technique));
    card.append(el("p", "flavor", p.flavor));
    const body = el("div", "body");
    const blocks = upgradeBlocks(p.blocks);
    blocks.forEach((b, i) => body.append(renderBlock(b, { key: `${rk()}|${p.id}`, i, blocks })));
    card.append(body);
    [...body.children].forEach((c, i) => { if (i) c.style.marginTop = "14px"; });
    card.append(scratchpad(`${rk()}|${p.id}`));

    const markSolved = (word) => {
      card.classList.add("solved");
      if (!head.querySelector(".badge")) head.append(el("span", "badge", "✓ Solved"));
      const w = el("div", "solved-word", word);
      card.querySelector(".answer")?.parentElement.replaceWith(w);
    };

    card.append(answerForm(async (v, fb) => {
      const h = await hash(rk(), v);
      if (h === p.hash) {
        st.solved[p.id] = v;
        st.times = st.times || {};
        st.times[p.id] = st.times[p.id] || Date.now();
        save(rk(), st);
        markSolved(v);
        updateProgress();
        renderLiveSplits();
        fillFitgrid();
        report("solve", p.id, v);
      } else if (p.partials && p.partials[h]) {
        fb.className = "feedback warn";
        fb.textContent = p.partials[h];
      } else {
        fb.className = "feedback bad";
        fb.textContent = `${v} is not the answer.`;
      }
    }));

    card.append(hintBox(p.id, p.hints || [p.hint], st));
    if (st.solved[p.id]) markSolved(st.solved[p.id]);
    return card;
  }

  function renderMeta(m, st) {
    const card = el("article", "card");
    card.append(el("span", "num", "METAPUZZLE"), el("h2", null, m.title), el("p", "flavor", m.flavor));
    if (m.explain) card.append(el("p", "explain", "How it works: " + m.explain));
    const body = el("div", "body");
    m.blocks.forEach((b, i) => body.append(renderBlock(b, b.type === "fitgrid" ? null : { key: `${rk()}|meta`, i, blocks: m.blocks })));
    const blanks = el("div", "blanks");
    for (let i = 0; i < m.length; i++) blanks.append(el("div", "blank", st.meta ? st.meta[i] : ""));
    body.append(blanks);
    card.append(body);

    const win = (word) => {
      const w = el("div", "win");
      w.append(el("div", "big", word));
      const nh = st.hints.length;
      w.append(el("p", "flavor", `Round complete. ${Object.keys(st.solved).length} of ${puzzle.puzzles.length} feeders solved, ${nh} hint${nh === 1 ? "" : "s"} used.`));
      const rows = splits(st);
      if (rows.length) {
        const t = el("table", "sol-table splits");
        const hr = el("tr");
        ["", "Puzzle", "Split", "Clock"].forEach((h) => hr.append(el("th", null, h)));
        t.append(hr);
        rows.forEach((r, i) => {
          const tr = el("tr", r.id === "meta" ? "meta-row" : null);
          [i + 1, r.title + (r.hint ? " (hint)" : ""), "+" + hms(r.split), hms(r.at)].forEach((c) => tr.append(el("td", null, String(c))));
          t.append(tr);
        });
        w.append(t);
      }
      const actions = el("div", "share-actions");
      const copy = el("button", "btn", "Share your run");
      copy.type = "button";
      const fb = el("span", "note");
      copy.addEventListener("click", async () => {
        const text = shareText(st);
        try {
          if (navigator.share && matchMedia("(pointer: coarse)").matches) await navigator.share({ text });
          else { await navigator.clipboard.writeText(text); fb.textContent = "Copied: results and a link to your splits."; }
        } catch { fb.textContent = shareLink(st); }
      });
      const view = el("a", "btn secondary", "View share page");
      view.href = shareLink(st);
      view.target = "_blank";
      view.rel = "noopener";
      const mine = el("a", "btn secondary", "My rounds");
      mine.href = "progress.html";
      actions.append(copy, view, mine);
      if (me()) {
        const hist = el("a", "btn secondary", "Your stats");
        hist.href = "share.html?player=" + encodeURIComponent(me().name);
        actions.append(hist);
      }
      w.append(actions, fb);
      card.querySelector(".answer")?.parentElement.replaceWith(w);
      [...blanks.children].forEach((b, i) => { b.textContent = word[i]; });
    };

    card.append(answerForm(async (v, fb) => {
      if (v.length !== m.length) {
        fb.className = "feedback bad";
        fb.textContent = `The final answer has ${m.length} letters.`;
        return;
      }
      if ((await hash(rk(), v)) === m.hash) {
        st.meta = v;
        st.times = st.times || {};
        st.times.meta = st.times.meta || Date.now();
        save(rk(), st);
        win(v);
        updateProgress();
        renderLiveSplits();
        report("solve", "meta", v);
      } else {
        fb.className = "feedback bad";
        fb.textContent = `${v} is not the final answer.`;
      }
    }, "Final answer"));
    card.append(scratchpad(`${rk()}|meta`));
    if (m.hints) card.append(hintBox("meta", m.hints, st));
    if (st.meta) win(st.meta);
    return card;
  }

  async function renderSolution() {
    const box = $("#solution");
    box.innerHTML = "";
    let sol;
    try {
      const path = levelPath("solutions", puzzle.date, difficulty);
      const r = await fetch(path, { cache: "no-cache" });
      if (!r.ok) return;
      sol = await r.json();
    } catch { return; }
    const card = el("article", "card");
    const btn = el("button", "btn secondary", "Reveal the solution");
    card.append(el("span", "num", "SOLUTION"), el("h2", null, "Solution published"), btn);
    btn.addEventListener("click", () => {
      btn.remove();
      card.append(el("p", null, `Final answer: ${sol.final}. ${sol.explain}`));
      const t = el("table", "sol-table");
      const hr = el("tr");
      ["#", "Title", "Answer", "Mechanism"].forEach((h) => hr.append(el("th", null, h)));
      t.append(hr);
      sol.puzzles.forEach((q) => {
        const tr = el("tr");
        let mech = q.mechanism + (q.transform ? ` + ${q.transform}` : "");
        if (q.mutated) mech += ` (encoded as ${q.mutated})`;
        [q.id, q.title, q.answer, mech].forEach((c) => tr.append(el("td", null, String(c))));
        t.append(tr);
      });
      card.append(t);
    });
    box.append(card);
  }

  // ---------- leaderboard ----------
  const fmtTime = (s) => {
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
    return h ? `${h}h ${String(m).padStart(2, "0")}m` : `${m}m ${String(sec).padStart(2, "0")}s`;
  };
  let boardView = "today";

  async function renderLeaderboard() {
    const box = $("#leaderboard");
    if (!box || (!API && !["localhost", "127.0.0.1"].includes(location.hostname))) return;
    const card = el("article", "card board-card");
    const head = el("div", "card-head");
    head.append(el("span", "num", "LEADERBOARD · " + difficulty.toUpperCase()));
    const tabs = el("div", "tabs");
    [["today", "This round"], ["alltime", "All time"]].forEach(([k, label]) => {
      const b = el("button", "tab" + (boardView === k ? " on" : ""), label);
      b.type = "button";
      b.addEventListener("click", () => { boardView = k; renderLeaderboard(); });
      tabs.append(b);
    });
    head.append(tabs);
    card.append(head);
    const status = el("p", "note", "Loading… (the leaderboard server may take a moment to wake up)");
    card.append(status);

    const player = me();
    if (!player) {
      const form = el("form", "answer join");
      const input = el("input");
      input.placeholder = "Pick a display name to join";
      input.maxLength = 24;
      input.setAttribute("aria-label", "Display name");
      const btn = el("button", "btn", "Join");
      btn.type = "submit";
      const fb = el("div", "feedback");
      form.append(input, btn);
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
          const res = await api("/api/players", { name: input.value });
          try { localStorage.setItem("mh:player", JSON.stringify(res)); } catch {}
          // Anything already solved this round counts from now.
          const st = load(rk());
          // The server's clock starts now: it only trusts times it witnessed itself.
          await api("/api/start", { token: res.token, date: puzzle.date, difficulty }).catch(() => {});
          Object.entries(st.solved).forEach(([id, v]) => report("solve", Number(id), v));
          st.hints.forEach((id) => report("hint", id));
          if (st.meta) report("solve", "meta", st.meta);
          renderLeaderboard();
        } catch (err) {
          fb.className = "feedback bad";
          fb.textContent = err.message;
        }
      });
      card.append(form, fb);
    } else {
      const note = el("p", "note", `Playing as ${player.name}. "Meta" is timed from 00:00 UTC on the round's date plus 5 minutes per hint; "Your clock" runs from when you first opened the round. `);
      const a = el("a", null, "Your stats →");
      a.href = "share.html?player=" + encodeURIComponent(player.name);
      note.append(a);
      card.append(note);
    }
    box.replaceChildren(card);

    try {
      const q = `difficulty=${difficulty}`;
      const data = boardView === "today"
        ? await api(`/api/leaderboard?date=${puzzle.date}&${q}`)
        : await api(`/api/alltime?${q}`);
      const t = el("table", "sol-table board-table");
      const hr = el("tr");
      const cols = boardView === "today" ? ["#", "Name", "Meta", "Your clock", "Feeders", "Hints"] : ["#", "Name", "Metas solved"];
      cols.forEach((h) => hr.append(el("th", null, h)));
      t.append(hr);
      data.rows.forEach((r, i) => {
        const tr = el("tr", player && r.name === player.name ? "me" : null);
        const cells = boardView === "today"
          ? [i + 1, r.name, r.meta ? fmtTime(r.score) : "—", r.personal != null ? hms(r.personal) : "—", `${r.feeders}/${r.total}`, r.hints]
          : [i + 1, r.name, r.metas];
        cells.forEach((c, j) => {
          const td = el("td");
          if (j === 1) {
            const a = el("a", null, String(c));
            a.href = "share.html?player=" + encodeURIComponent(r.name);
            td.append(a);
          } else td.textContent = String(c);
          tr.append(td);
        });
        t.append(tr);
      });
      status.replaceWith(data.rows.length ? t : el("p", "note", "Nobody on the board yet. Be the first."));
    } catch {
      status.textContent = "The leaderboard is offline right now; your progress is still saved in this browser.";
    }
  }

  // Date picker labels carry your saved status: ✓ solved, ◐ in progress (H = hard, E = easy).
  function markFor(key) {
    const st = load(key);
    if (st.meta) return "✓";
    if (Object.keys(st.solved).length || st.hints.length) return "◐";
    return "";
  }
  function refreshArchiveMarks() {
    const byDate = Object.fromEntries(index.puzzles.map((p) => [p.date, p]));
    [...$("#archive").options].forEach((o) => {
      const p = byDate[o.value];
      const h = markFor(p.date), m = p.medium ? markFor(p.date + "/medium") : "", e = p.easy ? markFor(p.date + "/easy") : "";
      const marks = [e && "E" + e, m && "M" + m, h && "H" + h].filter(Boolean).join(" ");
      o.textContent = `#${p.number} · ${p.date} · ${p.round}${marks ? "  " + marks : ""}`;
    });
  }

  function updateProgress() {
    const st = load(rk());
    const n = Object.keys(st.solved).length;
    let s = `${n}/${puzzle.puzzles.length} solved`;
    if (st.hints.length) s += ` · ${st.hints.length} hint${st.hints.length === 1 ? "" : "s"}`;
    if (st.meta) s += " · meta ✓";
    $("#progress").textContent = s;
    refreshArchiveMarks();
  }

  function tickTimer() {
    const t = $("#timer");
    if (!t || !puzzle) return;
    const st = load(rk());
    if (!st.start) { t.textContent = ""; return; }
    const end = st.times && st.times.meta ? st.times.meta : Date.now();
    t.textContent = `⏱ ${hms((end - st.start) / 1000)}${st.times && st.times.meta ? " (finished)" : ""}`;
  }

  function tickCountdown() {
    const now = new Date();
    const next = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1);
    const ms = next - now.getTime();
    const h = Math.floor(ms / 3.6e6), m = Math.floor((ms % 3.6e6) / 6e4);
    $("#countdown").textContent = `next round in ${h}h ${String(m).padStart(2, "0")}m`;
  }

  async function show(date, diff) {
    const entry = index.puzzles.find((x) => x.date === date);
    if (!hasLevel(entry, diff)) diff = "hard"; // early rounds had no easy or medium version
    difficulty = diff;
    const path = levelPath("puzzles", date, diff);
    const r = await fetch(path, { cache: "no-cache" });
    if (!r.ok) { $("#round").textContent = "Puzzle not found"; return; }
    puzzle = await r.json();
    const st = load(rk());
    const d = new Date(date + "T00:00:00Z");
    $("#eyebrow").textContent = `No. ${puzzle.number} · ${diff !== "hard" ? LEVEL[diff] + " · " : ""}${d.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric", year: "numeric", timeZone: "UTC" })}`;
    $("#round").textContent = puzzle.round;
    $("#intro").textContent = puzzle.intro;
    const echo = $("#echo");
    echo.textContent = puzzle.echo || "";
    echo.hidden = !puzzle.echo;
    document.title = `${puzzle.round}${diff !== "hard" ? ` (${LEVEL[diff]})` : ""} · Daily Metahunt`;
    document.querySelectorAll(".diff button").forEach((b) => {
      b.classList.toggle("on", b.dataset.diff === diff);
      b.disabled = !hasLevel(entry, b.dataset.diff);
    });
    if (st.start) renderRound(st);
    else renderGate(st);  // nothing is shown, and no clock runs, until you press Begin
    tickTimer();
    renderSolution();
    renderLeaderboard();

    const dates = index.puzzles.map((x) => x.date);
    const i = dates.indexOf(date);
    $("#archive").value = date;
    $("#prev").disabled = i <= 0;
    $("#next").disabled = i >= dates.length - 1;
  }

  function renderRound(st) {
    const list = $("#puzzles");
    list.innerHTML = "";
    puzzle.puzzles.forEach((p) => list.append(renderPuzzle(p, st)));
    $("#meta").innerHTML = "";
    $("#meta").append(renderMeta(puzzle.meta, st));
    fillFitgrid();
    updateProgress();
    renderLiveSplits();
  }

  // The "Ready?" screen: the round stays hidden until you choose to start the clock.
  function renderGate(st) {
    const key = rk();
    $("#livesplits").innerHTML = "";
    $("#meta").innerHTML = "";
    $("#progress").textContent = "";
    const card = el("article", "card gate");
    card.append(el("span", "num", `${LEVEL[difficulty].toUpperCase()} ROUND`));
    card.append(el("h2", "gate-title", "Ready?"));
    const n = puzzle.puzzles.length;
    card.append(el("p", "gate-copy",
      `${n} puzzles and a meta are waiting behind this door. Your clock starts the moment you press Begin, and a split is recorded every time you solve something.`));
    if (me()) card.append(el("p", "note", `You're on the leaderboard as ${me().name}; your server clock starts with Begin too.`));
    const btn = el("button", "btn gate-btn", "Begin");
    btn.type = "button";
    const count = el("div", "countdown");
    count.setAttribute("aria-live", "assertive");
    btn.addEventListener("click", () => {
      btn.remove();
      const steps = ["3", "2", "1", "Go!"];
      let i = 0;
      const tick = () => {
        if (rk() !== key) return;  // navigated away mid-countdown
        if (i < steps.length) {
          count.textContent = steps[i++];
          count.classList.remove("pop");
          void count.offsetWidth;  // restart the animation
          count.classList.add("pop");
          setTimeout(tick, 700);
          return;
        }
        const fresh = load(key);
        fresh.start = fresh.start || Date.now();
        save(key, fresh);
        if (me()) api("/api/start", { token: me().token, date: puzzle.date, difficulty }).catch(() => {});
        renderRound(fresh);
        tickTimer();
        $("#puzzles").scrollIntoView({ behavior: "smooth", block: "start" });
      };
      tick();
    });
    card.append(btn, count);
    const list = $("#puzzles");
    list.innerHTML = "";
    list.append(card);
  }

  // Live splits: every solve so far, plus how long you've been on the current split.
  function renderLiveSplits() {
    const box = $("#livesplits");
    if (!box || !puzzle) return;
    const st = load(rk());
    if (!st.start) { box.innerHTML = ""; return; }
    const rows = splits(st);
    const wrap = el("div", "livesplits");
    rows.forEach((r) => {
      const chip = el("div", "split-chip" + (r.id === "meta" ? " meta" : "") + (r.hint ? " hinted" : ""));
      chip.append(el("span", "split-name", r.id === "meta" ? "★ Meta" : String(r.id).padStart(2, "0") + " " + r.title),
        el("span", "split-time", "+" + hms(r.split)), el("span", "split-at", hms(r.at)));
      wrap.append(chip);
    });
    if (!(st.times && st.times.meta)) {
      const cur = el("div", "split-chip current");
      cur.append(el("span", "split-name", "Current split"), el("span", "split-time", ""), el("span", "split-at", ""));
      wrap.append(cur);
    }
    box.replaceChildren(wrap);
    updateCurrentSplit();
  }

  function updateCurrentSplit() {
    const cur = document.querySelector(".split-chip.current");
    if (!cur || !puzzle) return;
    const st = load(rk());
    if (!st.start) return;
    const rows = splits(st);
    const last = rows.length ? st.start + rows[rows.length - 1].at * 1000 : st.start;
    cur.querySelector(".split-time").textContent = "+" + hms((Date.now() - last) / 1000);
  }

  const go = (date, diff) => { location.hash = diff !== "hard" ? `${date}/${diff}` : date; };

  function route() {
    const [want, diff] = location.hash.slice(1).split("/");
    const dates = index.puzzles.map((x) => x.date);
    show(dates.includes(want) ? want : index.latest, ["easy", "medium"].includes(diff) ? diff : "hard");
  }

  async function init() {
    try {
      index = await (await fetch("puzzles/index.json", { cache: "no-cache" })).json();
    } catch {
      $("#round").textContent = "No puzzles yet";
      return;
    }
    const sel = $("#archive");
    [...index.puzzles].reverse().forEach((p) => {
      const o = el("option");
      o.value = p.date;
      sel.append(o);
    });
    refreshArchiveMarks();
    sel.addEventListener("change", () => go(sel.value, difficulty));
    const step = (k) => {
      const dates = index.puzzles.map((x) => x.date);
      const i = dates.indexOf(puzzle.date) + k;
      if (i >= 0 && i < dates.length) go(dates[i], difficulty);
    };
    $("#prev").addEventListener("click", () => step(-1));
    $("#next").addEventListener("click", () => step(1));
    document.querySelectorAll(".diff button").forEach((b) => b.addEventListener("click", () => go(puzzle.date, b.dataset.diff)));
    window.addEventListener("hashchange", route);
    tickCountdown();
    setInterval(tickCountdown, 30000);
    setInterval(() => { tickTimer(); updateCurrentSplit(); }, 1000);
    route();
  }

  init();
})();
