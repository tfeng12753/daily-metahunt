(() => {
  const $ = (s) => document.querySelector(s);
  const el = (tag, cls, text) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  };
  const hms = (sec) => {
    sec = Math.max(0, Math.round(sec));
    const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
    return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  };

  // Same storage format the round pages write: "mh:<date>" and "mh:<date>/easy".
  const read = (key) => {
    try { return JSON.parse(localStorage.getItem("mh:" + key)); } catch { return null; }
  };

  function status(st, total) {
    if (!st) return { state: "none" };
    const solved = Object.keys(st.solved || {}).length;
    const hints = (st.hints || []).length;
    const clock = st.meta && st.start && st.times && st.times.meta ? (st.times.meta - st.start) / 1000 : null;
    let state = "none";
    if (st.meta) state = "done";
    else if (solved || (st.hints || []).length) state = "progress";
    else if (st.start) state = "opened";
    return { state, solved, total, hints, clock, meta: st.meta || null };
  }

  const MARK = { done: "✓", progress: "◐", opened: "○", none: "" };
  const LABEL = { done: "Solved", progress: "In progress", opened: "Opened", none: "Not started" };

  function streak(rows) {
    // Consecutive days, ending today or yesterday, with at least one meta solved.
    const done = new Set(rows.filter((r) => r.hard.state === "done" || r.easy.state === "done").map((r) => r.date));
    const day = new Date();
    let key = day.toISOString().slice(0, 10);
    if (!done.has(key)) { day.setUTCDate(day.getUTCDate() - 1); key = day.toISOString().slice(0, 10); }
    let n = 0;
    while (done.has(key)) { n++; day.setUTCDate(day.getUTCDate() - 1); key = day.toISOString().slice(0, 10); }
    return n;
  }

  function roundLink(date, diff) {
    return `./#${date}${diff === "easy" ? "/easy" : ""}`;
  }

  function renderTiles(rows) {
    const all = rows.flatMap((r) => [r.hard, r.easy]);
    const done = all.filter((s) => s.state === "done");
    const clocks = done.map((s) => s.clock).filter((c) => c != null);
    const tiles = [
      ["Metas solved", `${done.length}`],
      ["Hard / Easy", `${rows.filter((r) => r.hard.state === "done").length} / ${rows.filter((r) => r.easy.state === "done").length}`],
      ["Current streak", `${streak(rows)} day${streak(rows) === 1 ? "" : "s"}`],
      ["Best clock", clocks.length ? hms(Math.min(...clocks)) : "—"],
      ["Feeders solved", `${all.reduce((a, s) => a + (s.solved || 0), 0)}`],
      ["Hints used", `${all.reduce((a, s) => a + (s.hints || 0), 0)}`],
    ];
    const box = $("#tiles");
    tiles.forEach(([k, v]) => {
      const d = el("div", "stat");
      d.append(el("div", "stat-v", v), el("div", "stat-k", k));
      box.append(d);
    });
  }

  function renderCalendar(rows) {
    const byDate = Object.fromEntries(rows.map((r) => [r.date, r]));
    const months = [...new Set(rows.map((r) => r.date.slice(0, 7)))].sort().reverse();
    const box = $("#calendar");
    months.forEach((ym) => {
      const [y, m] = ym.split("-").map(Number);
      const card = el("article", "card cal-card");
      card.append(el("span", "num", new Date(Date.UTC(y, m - 1, 1)).toLocaleDateString(undefined, { month: "long", year: "numeric", timeZone: "UTC" }).toUpperCase()));
      const grid = el("div", "cal");
      ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].forEach((d) => grid.append(el("div", "cal-head", d)));
      const first = (new Date(Date.UTC(y, m - 1, 1)).getUTCDay() + 6) % 7;
      for (let i = 0; i < first; i++) grid.append(el("div", "cal-cell empty"));
      const days = new Date(Date.UTC(y, m, 0)).getUTCDate();
      for (let d = 1; d <= days; d++) {
        const date = `${ym}-${String(d).padStart(2, "0")}`;
        const r = byDate[date];
        const cell = el(r ? "a" : "div", "cal-cell" + (r ? "" : " empty"));
        cell.append(el("span", "cal-day", String(d)));
        if (r) {
          cell.href = roundLink(date, r.hard.state === "done" && r.easy.state !== "done" && r.hasEasy ? "easy" : "hard");
          cell.title = `${r.round}: Hard ${LABEL[r.hard.state].toLowerCase()}` + (r.hasEasy ? `, Easy ${LABEL[r.easy.state].toLowerCase()}` : "");
          const dots = el("span", "cal-dots");
          dots.append(el("span", "cal-dot " + r.hard.state, "H"));
          if (r.hasEasy) dots.append(el("span", "cal-dot " + r.easy.state, "E"));
          cell.append(dots);
        }
        grid.append(cell);
      }
      card.append(grid);
      box.append(card);
    });
    const legend = el("p", "note cal-legend");
    legend.textContent = "H = Hard, E = Easy.  Filled = solved · half = in progress · outline = opened.";
    box.append(legend);
  }

  function renderList(rows) {
    const card = el("article", "card");
    card.append(el("span", "num", "EVERY ROUND"));
    const t = el("table", "sol-table progress-table");
    const hr = el("tr");
    ["#", "Date", "Round", "Level", "Status", "Puzzles", "Clock", "Hints"].forEach((h) => hr.append(el("th", null, h)));
    t.append(hr);
    rows.forEach((r) => {
      [["hard", r.hard], ["easy", r.easy]].forEach(([diff, s]) => {
        if (diff === "easy" && !r.hasEasy) return;
        const tr = el("tr", "st-" + s.state);
        const link = el("a", null, r.round);
        link.href = roundLink(r.date, diff);
        const cells = [
          `#${r.number}`, r.date, link, diff === "easy" ? "Easy" : "Hard",
          `${MARK[s.state]} ${LABEL[s.state]}`.trim(),
          s.state === "none" ? "—" : `${s.solved}/${s.total ?? "?"}${s.meta ? " + meta" : ""}`,
          s.clock != null ? hms(s.clock) : "—",
          s.state === "none" ? "—" : String(s.hints),
        ];
        cells.forEach((c) => {
          const td = el("td");
          if (c instanceof Node) td.append(c); else td.textContent = c;
          tr.append(td);
        });
        t.append(tr);
      });
    });
    const wrap = el("div", "scroll-x");
    wrap.append(t);
    card.append(wrap);
    $("#list").append(card);
  }

  // ---------- backup ----------
  function exportProgress() {
    const data = {};
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k && k.startsWith("mh:")) data[k] = localStorage.getItem(k);
    }
    const blob = new Blob([JSON.stringify({ app: "daily-metahunt", exported: new Date().toISOString(), data }, null, 1)], { type: "application/json" });
    const a = el("a");
    a.href = URL.createObjectURL(blob);
    a.download = `metahunt-progress-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.append(a);
    a.click();
    a.remove();
    $("#backup-msg").textContent = `Exported ${Object.keys(data).length} saved item${Object.keys(data).length === 1 ? "" : "s"}.`;
  }

  function mergeRound(a, b) {
    // Keep the union of solves and hints, and the earliest times.
    const out = { ...a, ...b };
    out.solved = { ...(a.solved || {}), ...(b.solved || {}) };
    out.hints = [...new Set([...(a.hints || []), ...(b.hints || [])])];
    out.meta = a.meta || b.meta;
    out.start = Math.min(a.start || Infinity, b.start || Infinity);
    if (out.start === Infinity) delete out.start;
    out.times = { ...(b.times || {}) };
    for (const [k, v] of Object.entries(a.times || {})) out.times[k] = out.times[k] ? Math.min(out.times[k], v) : v;
    return out;
  }

  async function importProgress(file) {
    const msg = $("#backup-msg");
    try {
      const parsed = JSON.parse(await file.text());
      if (parsed.app !== "daily-metahunt" || typeof parsed.data !== "object") throw new Error("not a Daily Metahunt backup");
      let n = 0;
      for (const [k, v] of Object.entries(parsed.data)) {
        if (!k.startsWith("mh:") || typeof v !== "string") continue;
        if (k === "mh:player") {
          if (!localStorage.getItem(k)) localStorage.setItem(k, v);  // never overwrite a current identity
          continue;
        }
        const incoming = JSON.parse(v);
        const existing = JSON.parse(localStorage.getItem(k) || "null");
        localStorage.setItem(k, JSON.stringify(existing ? mergeRound(existing, incoming) : incoming));
        n++;
      }
      msg.textContent = `Imported ${n} round${n === 1 ? "" : "s"}. Reloading…`;
      setTimeout(() => location.reload(), 700);
    } catch (e) {
      msg.textContent = "Couldn't import that file: " + e.message;
    }
  }

  async function init() {
    $("#export").addEventListener("click", exportProgress);
    $("#import").addEventListener("change", (e) => { if (e.target.files[0]) importProgress(e.target.files[0]); });
    let index;
    try {
      index = await (await fetch("puzzles/index.json", { cache: "no-cache" })).json();
    } catch {
      $("#sub").textContent = "Couldn't load the round list.";
      return;
    }
    const rows = [...index.puzzles].reverse().map((p) => ({
      date: p.date, number: p.number, round: p.round, hasEasy: !!p.easy,
      hard: status(read(p.date), p.count && p.count.hard),
      easy: status(read(p.date + "/easy"), p.count && p.count.easy),
    }));
    const played = rows.filter((r) => r.hard.state !== "none" || r.easy.state !== "none").length;
    $("#sub").textContent = played
      ? `You've played ${played} of ${rows.length} day${rows.length === 1 ? "" : "s"} so far.`
      : "Nothing played in this browser yet. Pick a day below, or import a backup.";
    renderTiles(rows);
    renderCalendar(rows);
    renderList(rows);
  }

  init();
})();
