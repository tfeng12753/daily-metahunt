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

  function fitgrid(b) {
    const g = el("div", "fitgrid");
    b.rows.forEach((row) => {
      const r = el("div", "fitrow");
      for (let i = 0; i < row.len; i++) r.append(el("span", "fitcell" + (i === row.shade ? " shade" : "")));
      g.append(r);
    });
    return g;
  }

  function renderBlock(b) {
    switch (b.type) {
      case "mono": return el("pre", "mono" + (b.big ? " big" : "") + (b.wide ? " wide" : ""), b.text);
      case "prose": return el("p", "prose", b.text);
      case "board": return board(b);
      case "nonogram": return nonogram(b);
      case "fitgrid": return fitgrid(b);
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
    card.append(head, el("h2", null, p.title), el("p", "flavor", p.flavor));
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
      const h = await hash(puzzle.date, v);
      if (h === p.hash) {
        st.solved[p.id] = v;
        save(puzzle.date, st);
        markSolved(v);
        updateProgress();
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
      if (!confirm("Reveal the mechanism for this puzzle? It will be noted on your record.")) return;
      if (!st.hints.includes(p.id)) st.hints.push(p.id);
      save(puzzle.date, st);
      showHint();
      updateProgress();
    });
    card.append(hintBtn);
    if (st.hints.includes(p.id)) showHint();
    if (st.solved[p.id]) markSolved(st.solved[p.id]);
    return card;
  }

  function renderMeta(m, st) {
    const card = el("article", "card");
    card.append(el("span", "num", "METAPUZZLE"), el("h2", null, m.title), el("p", "flavor", m.flavor));
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
      card.querySelector(".answer")?.parentElement.replaceWith(w);
      [...blanks.children].forEach((b, i) => { b.textContent = word[i]; });
    };

    card.append(answerForm(async (v, fb) => {
      if (v.length !== m.length) {
        fb.className = "feedback bad";
        fb.textContent = `The final answer has ${m.length} letters.`;
        return;
      }
      if ((await hash(puzzle.date, v)) === m.hash) {
        st.meta = v;
        save(puzzle.date, st);
        win(v);
        updateProgress();
      } else {
        fb.className = "feedback bad";
        fb.textContent = `${v} is not the final answer.`;
      }
    }, "Final answer"));
    if (st.meta) win(st.meta);
    return card;
  }

  async function renderSolution(date) {
    const box = $("#solution");
    box.innerHTML = "";
    let sol;
    try {
      const r = await fetch(`solutions/${date}.json`, { cache: "no-cache" });
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

  function updateProgress() {
    const st = load(puzzle.date);
    const n = Object.keys(st.solved).length;
    let s = `${n}/${puzzle.puzzles.length} solved`;
    if (st.hints.length) s += ` · ${st.hints.length} hint${st.hints.length === 1 ? "" : "s"}`;
    if (st.meta) s += " · meta ✓";
    $("#progress").textContent = s;
  }

  function tickCountdown() {
    const now = new Date();
    const next = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1);
    const ms = next - now.getTime();
    const h = Math.floor(ms / 3.6e6), m = Math.floor((ms % 3.6e6) / 6e4);
    $("#countdown").textContent = `next round in ${h}h ${String(m).padStart(2, "0")}m`;
  }

  async function show(date) {
    const r = await fetch(`puzzles/${date}.json`, { cache: "no-cache" });
    if (!r.ok) { $("#round").textContent = "Puzzle not found"; return; }
    puzzle = await r.json();
    const st = load(date);
    const d = new Date(date + "T00:00:00Z");
    $("#eyebrow").textContent = `No. ${puzzle.number} · ${d.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric", year: "numeric", timeZone: "UTC" })}`;
    $("#round").textContent = puzzle.round;
    $("#intro").textContent = puzzle.intro;
    document.title = `${puzzle.round} · Daily Metahunt`;
    const list = $("#puzzles");
    list.innerHTML = "";
    puzzle.puzzles.forEach((p) => list.append(renderPuzzle(p, st)));
    $("#meta").innerHTML = "";
    $("#meta").append(renderMeta(puzzle.meta, st));
    updateProgress();
    renderSolution(date);

    const dates = index.puzzles.map((x) => x.date);
    const i = dates.indexOf(date);
    $("#archive").value = date;
    $("#prev").disabled = i <= 0;
    $("#next").disabled = i >= dates.length - 1;
  }

  function route() {
    const want = location.hash.slice(1);
    const dates = index.puzzles.map((x) => x.date);
    show(dates.includes(want) ? want : index.latest);
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
      const o = el("option", null, `#${p.number} · ${p.date} · ${p.round}`);
      o.value = p.date;
      sel.append(o);
    });
    sel.addEventListener("change", () => { location.hash = sel.value; });
    const step = (k) => {
      const dates = index.puzzles.map((x) => x.date);
      const i = dates.indexOf(puzzle.date) + k;
      if (i >= 0 && i < dates.length) location.hash = dates[i];
    };
    $("#prev").addEventListener("click", () => step(-1));
    $("#next").addEventListener("click", () => step(1));
    window.addEventListener("hashchange", route);
    tickCountdown();
    setInterval(tickCountdown, 30000);
    route();
  }

  init();
})();
