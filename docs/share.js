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
  const hms = (sec) => {
    sec = Math.max(0, Math.round(sec));
    const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
    return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  };
  const API = ["localhost", "127.0.0.1"].includes(location.hostname) ? "" : (window.METAHUNT_API || "");
  const getJSON = async (url) => {
    const r = await fetch(url, { cache: "no-cache" });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  };
  const roundPath = (date, diff) => (diff === "easy" ? `puzzles/easy/${date}.json` : `puzzles/${date}.json`);
  const dateLabel = (d) => new Date(d + "T00:00:00Z").toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric", year: "numeric", timeZone: "UTC" });

  function fail(msg) {
    $("#title").textContent = "Nothing to show";
    $("#sub").textContent = msg;
  }

  // ---------- one run, from the link ----------
  async function showRun(encoded) {
    let run;
    try {
      const json = decodeURIComponent(escape(atob(encoded.replace(/-/g, "+").replace(/_/g, "/"))));
      run = JSON.parse(json);
    } catch {
      return fail("This share link looks damaged.");
    }
    let round;
    try { round = await getJSON(roundPath(run.d, run.x)); } catch { return fail("That round could not be found."); }
    const titles = Object.fromEntries(round.puzzles.map((p) => [p.id, p.title]));
    const hintSet = new Set(run.s.filter((s) => s[2]).map((s) => s[0]));
    const solvedSet = new Set(run.s.map((s) => s[0]));

    $("#eyebrow").textContent = `No. ${round.number} · ${run.x === "easy" ? "Easy" : "Hard"} · ${dateLabel(run.d)}`;
    $("#title").textContent = round.round;
    $("#sub").textContent = run.n ? `${run.n}'s run` : "A solver's run";
    document.title = `${run.n ? run.n + " · " : ""}${round.round} · Daily Metahunt`;

    const card = el("article", "card");
    const big = el("div", "win");
    big.append(el("div", "big", run.m != null ? hms(run.m) : "Unfinished"));
    const squares = round.puzzles.map((p) => (solvedSet.has(p.id) ? (hintSet.has(p.id) ? "🟨" : "🟩") : "⬛")).join("") + (run.m != null ? " ⭐" : "");
    big.append(el("p", "squares", squares));
    big.append(el("p", "note", `${solvedSet.size}/${round.puzzles.length} feeders · ${hintSet.size} hint${hintSet.size === 1 ? "" : "s"} · personal clock from first opening the round`));
    card.append(big);

    // Timeline: each solve as a tick along the run.
    const events = run.s.map(([id, at, h]) => ({ label: `${id}`, title: titles[id] || `Puzzle ${id}`, at, hint: !!h }));
    if (run.m != null) events.push({ label: "★", title: "Meta", at: run.m, meta: true });
    events.sort((a, b) => a.at - b.at);
    const end = Math.max(1, ...events.map((e) => e.at));
    if (events.length) {
      const W = 640, H = 64, pad = 16;
      const s = svg("svg", { viewBox: `0 0 ${W} ${H}`, class: "timeline", role: "img", "aria-label": "Solve timeline" });
      s.append(svg("line", { x1: pad, y1: 36, x2: W - pad, y2: 36, stroke: "var(--line)", "stroke-width": 4, "stroke-linecap": "round" }));
      events.forEach((e) => {
        const x = pad + (W - 2 * pad) * (e.at / end);
        const c = svg("circle", { cx: x, cy: 36, r: e.meta ? 9 : 7, fill: e.meta ? "var(--accent)" : e.hint ? "var(--warn)" : "var(--good)" });
        const tip = svg("title", {});
        tip.textContent = `${e.title}: ${hms(e.at)}`;
        c.append(tip);
        s.append(c);
        const t = svg("text", { x, y: 18, "text-anchor": "middle", "font-size": 12, fill: "var(--muted)", "font-family": "IBM Plex Mono, monospace" });
        t.textContent = e.label;
        s.append(t);
      });
      const t0 = svg("text", { x: pad, y: 60, "font-size": 11, fill: "var(--muted)", "font-family": "IBM Plex Mono, monospace" });
      t0.textContent = "0:00:00";
      const t1 = svg("text", { x: W - pad, y: 60, "text-anchor": "end", "font-size": 11, fill: "var(--muted)", "font-family": "IBM Plex Mono, monospace" });
      t1.textContent = hms(end);
      s.append(t0, t1);
      card.append(s);

      const t = el("table", "sol-table splits");
      const hr = el("tr");
      ["", "Puzzle", "Split", "Clock"].forEach((h) => hr.append(el("th", null, h)));
      t.append(hr);
      events.forEach((e, i) => {
        const tr = el("tr", e.meta ? "meta-row" : null);
        const split = e.at - (i ? events[i - 1].at : 0);
        [i + 1, e.title + (e.hint ? " (hint)" : ""), "+" + hms(split), hms(e.at)].forEach((c) => tr.append(el("td", null, String(c))));
        t.append(tr);
      });
      card.append(t);
    }
    const verify = el("p", "note verify");
    card.append(verify);
    const actions = el("div", "share-actions");
    const play = el("a", "btn", "Play this round");
    play.href = `./#${run.d}${run.x === "easy" ? "/easy" : ""}`;
    actions.append(play);
    if (run.n) {
      const hist = el("a", "btn secondary", `All of ${run.n}'s rounds`);
      hist.href = "share.html?player=" + encodeURIComponent(run.n);
      actions.append(hist);
    }
    card.append(actions);
    $("#content").append(card);

    // Cross-check against what the leaderboard server recorded.
    if (run.n) {
      verify.textContent = "Checking the leaderboard's record…";
      try {
        const rec = await getJSON(`${API}/api/run?name=${encodeURIComponent(run.n)}&date=${run.d}&difficulty=${run.x}`);
        if (rec.solves.meta != null) {
          verify.textContent = `✓ Verified by the leaderboard: meta solved ${hms(rec.solves.meta)} after the round's release` +
            (rec.personal != null ? `, ${hms(rec.personal)} on the server's personal clock.` : ".");
          verify.classList.add("ok");
        } else {
          const n = Object.keys(rec.solves).length;
          verify.textContent = `The leaderboard has ${n} solve${n === 1 ? "" : "s"} recorded for ${rec.name} on this round, but no meta yet.`;
        }
      } catch {
        verify.textContent = "Not verified: the leaderboard has no record of this run, or is offline.";
      }
    } else {
      verify.textContent = "This solver wasn't on the leaderboard, so these times come from their browser only.";
    }
  }

  // ---------- a player's stored history ----------
  async function showPlayer(name) {
    $("#eyebrow").textContent = "Player stats";
    $("#title").textContent = name;
    document.title = `${name} · Daily Metahunt`;
    let data;
    try {
      data = await getJSON(`${API}/api/player?name=${encodeURIComponent(name)}`);
    } catch {
      $("#sub").textContent = "No stats found. The player may not exist, or the leaderboard is offline (it can take a moment to wake up).";
      return;
    }
    $("#title").textContent = data.name;
    const t = data.totals;
    $("#sub").textContent = `${t.metas} meta${t.metas === 1 ? "" : "s"} solved (${t.hard} hard, ${t.easy} easy)`;

    const tiles = el("div", "stat-tiles");
    [["Metas solved", String(t.metas)], ["Best clock", t.best != null ? hms(t.best) : "—"], ["Average clock", t.average != null ? hms(t.average) : "—"], ["Rounds played", String(data.rounds.length)]]
      .forEach(([k, v]) => {
        const d = el("div", "stat");
        d.append(el("div", "stat-v", v), el("div", "stat-k", k));
        tiles.append(d);
      });

    const card = el("article", "card");
    card.append(tiles);
    const tbl = el("table", "sol-table");
    const hr = el("tr");
    ["Date", "Level", "Feeders", "Hints", "Meta after release", "Personal clock"].forEach((h) => hr.append(el("th", null, h)));
    tbl.append(hr);
    data.rounds.forEach((r) => {
      const tr = el("tr");
      const a = el("a", null, r.date);
      a.href = `./#${r.date}${r.difficulty === "easy" ? "/easy" : ""}`;
      const td = el("td");
      td.append(a);
      tr.append(td);
      [r.difficulty, r.feeders, r.hints, r.meta ? hms(r.sinceRelease) : "—", r.personal != null ? hms(r.personal) : "—"]
        .forEach((c) => tr.append(el("td", null, String(c))));
      tbl.append(tr);
    });
    card.append(data.rounds.length ? tbl : el("p", "note", "No rounds recorded yet."));
    $("#content").append(card);
  }

  const run = location.hash.match(/run=([A-Za-z0-9_-]+)/);
  const player = new URLSearchParams(location.search).get("player");
  if (run) showRun(run[1]);
  else if (player) showPlayer(player);
  else fail("Share links come from the end of a solved round.");
})();
