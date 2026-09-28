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
  const rk = () => puzzle.salt || puzzle.date; // "2026-09-28" or "2026-09-28/easy"

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
    return `Daily Metahunt #${puzzle.number} ${difficulty === "easy" ? "(Easy)" : "(Hard)"}: ${puzzle.round}\n` +
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

  function board(b) {
    const t = el("table", "board" + (b.plain ? " plain" : ""));
    const files = "abcdefgh";
    b.rows.forEach((row, r) => {
      const tr = el("tr");
      if (!b.plain) tr.append(el("th", null, String(8 - r)));
      [...row].forEach((ch, c) => tr.append(el("td", !b.plain && (r + c) % 2 ? "dark" : null, ch)));
      t.append(tr);
    });
    if (!b.plain) {
      const tr = el("tr");
      tr.append(el("th"));
      [...files].forEach((f) => tr.append(el("th", null, f)));
      t.append(tr);
    }
    return t;
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
        if (c % 6 === 5) td.classList.add("gapcol");
        tr.append(td);
      }
      t.append(tr);
    }
    wrap.append(t);
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

  function renderBlock(b) {
    switch (b.type) {
      case "mono": return el("pre", "mono" + (b.big ? " big" : "") + (b.wide ? " wide" : ""), b.text);
      case "prose": return el("p", "prose", b.text);
      case "board": return board(b);
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
    p.blocks.forEach((b) => body.append(renderBlock(b)));
    card.append(body);
    [...body.children].forEach((c, i) => { if (i) c.style.marginTop = "14px"; });

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

    const hintBtn = el("button", "btn secondary", "Hint");
    hintBtn.style.marginTop = "12px";
    const showHint = () => { hintBtn.replaceWith(el("div", "hint", p.hint)); };
    hintBtn.addEventListener("click", () => {
      const penalty = me() ? " On the leaderboard it adds a 5-minute penalty." : "";
      if (!confirm("Reveal the mechanism for this puzzle? It will be noted on your record." + penalty)) return;
      if (!st.hints.includes(p.id)) st.hints.push(p.id);
      save(rk(), st);
      showHint();
      updateProgress();
      renderLiveSplits();
      report("hint", p.id);
    });
    card.append(hintBtn);
    if (st.hints.includes(p.id)) showHint();
    if (st.solved[p.id]) markSolved(st.solved[p.id]);
    return card;
  }

  function renderMeta(m, st) {
    const card = el("article", "card");
    card.append(el("span", "num", "METAPUZZLE"), el("h2", null, m.title), el("p", "flavor", m.flavor));
    if (m.explain) card.append(el("p", "explain", "How it works: " + m.explain));
    const body = el("div", "body");
    m.blocks.forEach((b) => body.append(renderBlock(b)));
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
    if (st.meta) win(st.meta);
    return card;
  }

  async function renderSolution() {
    const box = $("#solution");
    box.innerHTML = "";
    let sol;
    try {
      const path = difficulty === "easy" ? `solutions/easy/${puzzle.date}.json` : `solutions/${puzzle.date}.json`;
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
      const h = markFor(p.date), e = p.easy ? markFor(p.date + "/easy") : "";
      const marks = [h && "H" + h, e && "E" + e].filter(Boolean).join(" ");
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
    if (diff === "easy" && entry && !entry.easy) diff = "hard"; // early rounds had no easy version
    difficulty = diff;
    const path = diff === "easy" ? `puzzles/easy/${date}.json` : `puzzles/${date}.json`;
    const r = await fetch(path, { cache: "no-cache" });
    if (!r.ok) { $("#round").textContent = "Puzzle not found"; return; }
    puzzle = await r.json();
    const st = load(rk());
    const d = new Date(date + "T00:00:00Z");
    $("#eyebrow").textContent = `No. ${puzzle.number} · ${diff === "easy" ? "Easy · " : ""}${d.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric", year: "numeric", timeZone: "UTC" })}`;
    $("#round").textContent = puzzle.round;
    $("#intro").textContent = puzzle.intro;
    const echo = $("#echo");
    echo.textContent = puzzle.echo || "";
    echo.hidden = !puzzle.echo;
    document.title = `${puzzle.round}${diff === "easy" ? " (Easy)" : ""} · Daily Metahunt`;
    document.querySelectorAll(".diff button").forEach((b) => {
      b.classList.toggle("on", b.dataset.diff === diff);
      b.disabled = b.dataset.diff === "easy" && entry && !entry.easy;
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
    card.append(el("span", "num", difficulty === "easy" ? "EASY ROUND" : "HARD ROUND"));
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

  const go = (date, diff) => { location.hash = diff === "easy" ? `${date}/easy` : date; };

  function route() {
    const [want, diff] = location.hash.slice(1).split("/");
    const dates = index.puzzles.map((x) => x.date);
    show(dates.includes(want) ? want : index.latest, diff === "easy" ? "easy" : "hard");
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
