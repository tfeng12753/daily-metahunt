// Score storage: Postgres when DATABASE_URL is set, otherwise in memory (local dev only).

export async function createStore(databaseUrl) {
  return databaseUrl ? pgStore(databaseUrl) : memoryStore();
}

function memoryStore() {
  console.warn("DATABASE_URL not set: scores are kept in memory and lost on restart.");
  const players = [];
  const solves = new Map(); // key -> Date
  const hints = new Set();
  const starts = new Map(); // "id|date|difficulty" -> ms
  const k = ({ playerId, date, difficulty, puzzle }) => [playerId, date, difficulty, puzzle].join("|");
  return {
    kind: "memory",
    async createPlayer(name, tokenHash) {
      if (players.some((p) => p.name.toLowerCase() === name.toLowerCase())) return null;
      const p = { id: players.length + 1, name, tokenHash };
      players.push(p);
      return p;
    },
    async playerByTokenHash(h) {
      return players.find((p) => p.tokenHash === h) || null;
    },
    async recordSolve(key) {
      if (!solves.has(k(key))) solves.set(k(key), Date.now());
      return solves.get(k(key));
    },
    async recordHint(key) {
      hints.add(k(key));
    },
    async recordStart({ playerId, date, difficulty }) {
      const key = [playerId, date, difficulty].join("|");
      if (!starts.has(key)) starts.set(key, Date.now());
      return starts.get(key);
    },
    async playerByName(name) {
      return players.find((p) => p.name.toLowerCase() === String(name).toLowerCase()) || null;
    },
    async run(playerId, date, difficulty) {
      const out = { startedAt: starts.get([playerId, date, difficulty].join("|")) || null, solves: {}, hints: [] };
      for (const [key, at] of solves) {
        const [id, d, diff, puzzle] = key.split("|");
        if (+id === playerId && d === date && diff === difficulty) out.solves[puzzle] = at;
      }
      for (const key of hints) {
        const [id, d, diff, puzzle] = key.split("|");
        if (+id === playerId && d === date && diff === difficulty) out.hints.push(puzzle);
      }
      return out;
    },
    async history(playerId) {
      const rounds = new Map();
      const get = (d, diff) => {
        const key = d + "|" + diff;
        if (!rounds.has(key)) rounds.set(key, { date: d, difficulty: diff, feeders: 0, metaAt: null, startedAt: starts.get([playerId, d, diff].join("|")) || null, hints: 0 });
        return rounds.get(key);
      };
      for (const [key, at] of solves) {
        const [id, d, diff, puzzle] = key.split("|");
        if (+id !== playerId) continue;
        if (puzzle === "meta") get(d, diff).metaAt = at;
        else get(d, diff).feeders++;
      }
      for (const key of hints) {
        const [id, d, diff] = key.split("|");
        if (+id === playerId) get(d, diff).hints++;
      }
      return [...rounds.values()].sort((a, b) => b.date.localeCompare(a.date) || a.difficulty.localeCompare(b.difficulty));
    },
    async roundRows(date, difficulty) {
      const rows = new Map();
      const row = (id) => {
        if (!rows.has(id)) rows.set(id, { name: players[id - 1].name, feeders: 0, metaAt: null, hints: 0, startedAt: starts.get([id, date, difficulty].join("|")) || null });
        return rows.get(id);
      };
      for (const [key, at] of solves) {
        const [id, d, diff, puzzle] = key.split("|");
        if (d !== date || diff !== difficulty) continue;
        if (puzzle === "meta") row(+id).metaAt = at;
        else row(+id).feeders++;
      }
      for (const key of hints) {
        const [id, d, diff] = key.split("|");
        if (d === date && diff === difficulty) row(+id).hints++;
      }
      return [...rows.values()];
    },
    async allTime(difficulty) {
      const tally = new Map();
      for (const key of solves.keys()) {
        const [id, , diff, puzzle] = key.split("|");
        if (diff !== difficulty || puzzle !== "meta") continue;
        tally.set(+id, (tally.get(+id) || 0) + 1);
      }
      return [...tally].map(([id, metas]) => ({ name: players[id - 1].name, metas }))
        .sort((a, b) => b.metas - a.metas).slice(0, 100);
    },
  };
}

async function pgStore(url) {
  const { default: pg } = await import("pg");
  const pool = new pg.Pool({ connectionString: url, ssl: /localhost|127\.0\.0\.1/.test(url) ? false : { rejectUnauthorized: false }, max: 5 });
  await pool.query(`
    create table if not exists players (
      id serial primary key,
      name text not null,
      token_hash text not null unique,
      created_at timestamptz not null default now()
    );
    create unique index if not exists players_name_lower on players (lower(name));
    create table if not exists solves (
      player_id int not null references players(id),
      date text not null,
      difficulty text not null,
      puzzle text not null,
      solved_at timestamptz not null default now(),
      primary key (player_id, date, difficulty, puzzle)
    );
    create table if not exists starts (
      player_id int not null references players(id),
      date text not null,
      difficulty text not null,
      started_at timestamptz not null default now(),
      primary key (player_id, date, difficulty)
    );
    create table if not exists hints (
      player_id int not null references players(id),
      date text not null,
      difficulty text not null,
      puzzle text not null,
      primary key (player_id, date, difficulty, puzzle)
    );
  `);
  return {
    kind: "postgres",
    async createPlayer(name, tokenHash) {
      try {
        const { rows } = await pool.query("insert into players (name, token_hash) values ($1, $2) returning id, name", [name, tokenHash]);
        return rows[0];
      } catch (e) {
        if (e.code === "23505") return null; // unique violation: name taken
        throw e;
      }
    },
    async playerByTokenHash(h) {
      const { rows } = await pool.query("select id, name from players where token_hash = $1", [h]);
      return rows[0] || null;
    },
    async recordSolve({ playerId, date, difficulty, puzzle }) {
      await pool.query(
        "insert into solves (player_id, date, difficulty, puzzle) values ($1, $2, $3, $4) on conflict do nothing",
        [playerId, date, difficulty, puzzle]);
      const { rows } = await pool.query(
        "select solved_at from solves where player_id = $1 and date = $2 and difficulty = $3 and puzzle = $4",
        [playerId, date, difficulty, puzzle]);
      return rows[0].solved_at.getTime();
    },
    async recordHint({ playerId, date, difficulty, puzzle }) {
      await pool.query(
        "insert into hints (player_id, date, difficulty, puzzle) values ($1, $2, $3, $4) on conflict do nothing",
        [playerId, date, difficulty, puzzle]);
    },
    async recordStart({ playerId, date, difficulty }) {
      await pool.query("insert into starts (player_id, date, difficulty) values ($1, $2, $3) on conflict do nothing", [playerId, date, difficulty]);
      const { rows } = await pool.query("select started_at from starts where player_id = $1 and date = $2 and difficulty = $3", [playerId, date, difficulty]);
      return rows[0].started_at.getTime();
    },
    async playerByName(name) {
      const { rows } = await pool.query("select id, name from players where lower(name) = lower($1)", [String(name)]);
      return rows[0] || null;
    },
    async run(playerId, date, difficulty) {
      const q = [playerId, date, difficulty];
      const [st, sv, hn] = await Promise.all([
        pool.query("select started_at from starts where player_id = $1 and date = $2 and difficulty = $3", q),
        pool.query("select puzzle, solved_at from solves where player_id = $1 and date = $2 and difficulty = $3", q),
        pool.query("select puzzle from hints where player_id = $1 and date = $2 and difficulty = $3", q),
      ]);
      return {
        startedAt: st.rows[0] ? st.rows[0].started_at.getTime() : null,
        solves: Object.fromEntries(sv.rows.map((r) => [r.puzzle, r.solved_at.getTime()])),
        hints: hn.rows.map((r) => r.puzzle),
      };
    },
    async history(playerId) {
      const { rows } = await pool.query(`
        select s.date, s.difficulty,
               count(*) filter (where s.puzzle <> 'meta')::int as feeders,
               max(s.solved_at) filter (where s.puzzle = 'meta') as meta_at,
               (select started_at from starts t where t.player_id = $1 and t.date = s.date and t.difficulty = s.difficulty) as started_at,
               (select count(*)::int from hints h where h.player_id = $1 and h.date = s.date and h.difficulty = s.difficulty) as hints
          from solves s
         where s.player_id = $1
         group by s.date, s.difficulty
         order by s.date desc, s.difficulty asc
         limit 400`, [playerId]);
      return rows.map((r) => ({ date: r.date, difficulty: r.difficulty, feeders: r.feeders, hints: r.hints,
        metaAt: r.meta_at ? r.meta_at.getTime() : null, startedAt: r.started_at ? r.started_at.getTime() : null }));
    },
    async roundRows(date, difficulty) {
      const { rows } = await pool.query(`
        select p.name,
               (select started_at from starts t where t.player_id = p.id and t.date = $1 and t.difficulty = $2) as started_at,
               count(*) filter (where s.puzzle <> 'meta')::int as feeders,
               max(s.solved_at) filter (where s.puzzle = 'meta') as meta_at,
               (select count(*)::int from hints h
                 where h.player_id = p.id and h.date = $1 and h.difficulty = $2) as hints
          from solves s join players p on p.id = s.player_id
         where s.date = $1 and s.difficulty = $2
         group by p.id, p.name`, [date, difficulty]);
      return rows.map((r) => ({ name: r.name, feeders: r.feeders, metaAt: r.meta_at ? r.meta_at.getTime() : null, hints: r.hints,
        startedAt: r.started_at ? r.started_at.getTime() : null }));
    },
    async allTime(difficulty) {
      const { rows } = await pool.query(`
        select p.name, count(*)::int as metas
          from solves s join players p on p.id = s.player_id
         where s.difficulty = $1 and s.puzzle = 'meta'
         group by p.id, p.name
         order by metas desc, min(s.solved_at) asc
         limit 100`, [difficulty]);
      return rows;
    },
  };
}
