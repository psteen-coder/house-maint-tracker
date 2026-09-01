import { useEffect, useMemo, useState } from "react";
import { api, getToken, setToken } from "./api.js";

const THEMES = ["light", "dark", "forest", "terracotta", "slate"];

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme || "light";
  localStorage.setItem("house-maint-theme", theme || "light");
}

export default function App() {
  const [user, setUser] = useState(null);
  const [house, setHouse] = useState(null);
  const [view, setView] = useState("board");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    applyTheme(localStorage.getItem("house-maint-theme") || "light");
    if (!getToken()) return;
    api("/api/me")
      .then((d) => {
        setUser(d.user);
        setHouse(d.house);
        applyTheme(d.user.theme);
      })
      .catch(() => setToken(null));
  }, []);

  async function onLogin(email, password) {
    setError("");
    setBusy(true);
    try {
      const d = await api("/api/auth/login", { method: "POST", body: { email, password } });
      setToken(d.token);
      setUser(d.user);
      applyTheme(d.user.theme);
      const me = await api("/api/me");
      setHouse(me.house);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function onLogout() {
    try {
      await api("/api/auth/logout", { method: "POST" });
    } catch {
      /* ignore */
    }
    setToken(null);
    setUser(null);
  }

  async function onTheme(theme) {
    applyTheme(theme);
    if (!user) return;
    const u = await api("/api/me/theme", { method: "PATCH", body: { theme } });
    setUser(u);
  }

  if (!user) {
    return <Login onLogin={onLogin} error={error} busy={busy} />;
  }

  return (
    <div className="app">
      <header className="top">
        <div>
          <p className="eyebrow">1944 Dinius · Raisin Township</p>
          <h1>House Maint Tracker</h1>
        </div>
        <nav>
          {["board", "calendar", "tasks", "people", "weather"].map((v) => (
            <button
              key={v}
              data-testid={`nav-${v}`}
              className={view === v ? "active" : ""}
              onClick={() => setView(v)}
            >
              {v}
            </button>
          ))}
        </nav>
        <div className="who">
          <label>
            Theme
            <select value={user.theme} onChange={(e) => onTheme(e.target.value)} data-testid="theme-select">
              {THEMES.map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
          </label>
          <span>
            {user.name} · {user.role}
          </span>
          <button onClick={onLogout}>Sign out</button>
        </div>
      </header>
      {view === "board" && <Board user={user} />}
      {view === "calendar" && <CalendarView />}
      {view === "tasks" && <Tasks user={user} />}
      {view === "people" && <People user={user} />}
      {view === "weather" && <Weather house={house} user={user} />}
    </div>
  );
}

function Login({ onLogin, error, busy }) {
  const [email, setEmail] = useState("patrick@1944dinius.local");
  const [password, setPassword] = useState("adminpass");
  return (
    <div className="login">
      <div className="card login-card">
        <p className="eyebrow">Household ops</p>
        <h1>House Maint Tracker</h1>
        <p className="lede">1944 Dinius Road — gutters, filters, and the rest of the list.</p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onLogin(email, password);
          }}
        >
          <label>
            Email
            <input value={email} onChange={(e) => setEmail(e.target.value)} data-testid="login-email" />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              data-testid="login-password"
            />
          </label>
          {error && <p className="error">{error}</p>}
          <button type="submit" disabled={busy} data-testid="login-submit">
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <p className="hint">
          Seeded: patrick@1944dinius.local / adminpass · alex / memberpass · jamie / viewerpass
        </p>
      </div>
    </div>
  );
}

function Card({ item, users, canMutate, onPatch }) {
  return (
    <article className="ticket" data-testid="ticket">
      <header>
        <strong>{item.title}</strong>
        <span className="mins">{item.estimated_minutes} min</span>
      </header>
      <p className="meta">
        Due {item.due_date}
        {item.weather_adjusted ? " · weather-shifted" : ""}
        {item.blocked ? ` · ${item.block_reason}` : ""}
      </p>
      {item.conditions?.length > 0 && (
        <ul className="chips">
          {item.conditions.map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ul>
      )}
      <p className="assignee">Assigned: {item.assignee_name || "unassigned"}</p>
      {canMutate && (
        <div className="row">
          {item.status !== "in_progress" && item.status !== "done" && (
            <button disabled={item.blocked} onClick={() => onPatch(item.id, { status: "in_progress" })}>
              Start
            </button>
          )}
          {item.status !== "done" && (
            <button disabled={item.blocked} onClick={() => onPatch(item.id, { status: "done" })}>
              Complete
            </button>
          )}
          <select
            value={item.assignee_id || ""}
            onChange={(e) => onPatch(item.id, { assignee_id: Number(e.target.value) })}
          >
            <option value="">unassigned</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name}
              </option>
            ))}
          </select>
        </div>
      )}
    </article>
  );
}

function Board({ user }) {
  const [board, setBoard] = useState({ due: [], in_progress: [], completed: [] });
  const [users, setUsers] = useState([]);
  const [err, setErr] = useState("");
  const canMutate = user.role !== "viewer";

  async function load() {
    const [b, u] = await Promise.all([api("/api/kanban"), api("/api/users")]);
    setBoard(b);
    setUsers(u);
  }
  useEffect(() => {
    load().catch((e) => setErr(e.message));
  }, []);

  async function onPatch(id, body) {
    setErr("");
    try {
      await api(`/api/occurrences/${id}`, { method: "PATCH", body });
      await load();
    } catch (e) {
      setErr(e.message);
    }
  }

  const cols = [
    ["due", "Due within a week"],
    ["in_progress", "In progress"],
    ["completed", "Completed (past week)"],
  ];
  return (
    <section>
      {err && <p className="error">{err}</p>}
      <div className="kanban" data-testid="kanban">
        {cols.map(([key, label]) => (
          <div key={key} className="col" data-testid={`col-${key}`}>
            <h2>
              {label} <em>{board[key].length}</em>
            </h2>
            {board[key].map((item) => (
              <Card key={item.id} item={item} users={users} canMutate={canMutate} onPatch={onPatch} />
            ))}
            {board[key].length === 0 && <p className="empty">Nothing here.</p>}
          </div>
        ))}
      </div>
    </section>
  );
}

function CalendarView() {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [data, setData] = useState({ days: {} });
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    api(`/api/calendar?year=${year}&month=${month}`).then(setData);
    setSelected(null);
  }, [year, month]);

  const first = new Date(year, month - 1, 1);
  const startPad = first.getDay();
  const daysInMonth = new Date(year, month, 0).getDate();
  const cells = [];
  for (let i = 0; i < startPad; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);

  const selectedKey = selected ? `${year}-${String(month).padStart(2, "0")}-${String(selected).padStart(2, "0")}` : null;
  const selectedItems = selectedKey ? data.days[selectedKey] || [] : [];

  return (
    <section className="cal-wrap" data-testid="calendar">
      <div className="row">
        <button onClick={() => (month === 1 ? (setMonth(12), setYear(year - 1)) : setMonth(month - 1))}>‹</button>
        <h2>
          {first.toLocaleString("en-US", { month: "long", year: "numeric" })}
        </h2>
        <button onClick={() => (month === 12 ? (setMonth(1), setYear(year + 1)) : setMonth(month + 1))}>›</button>
      </div>
      <div className="cal-grid">
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
          <div key={d} className="dow">
            {d}
          </div>
        ))}
        {cells.map((d, i) => {
          if (!d) return <div key={`e${i}`} className="cell empty-cell" />;
          const key = `${year}-${String(month).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
          const items = data.days[key] || [];
          return (
            <button
              key={key}
              className={`cell ${selected === d ? "sel" : ""}`}
              onClick={() => setSelected(d)}
            >
              <span>{d}</span>
              {items.length > 0 && <em>{items.length}</em>}
            </button>
          );
        })}
      </div>
      <div className="day-detail">
        {selected ? (
          <>
            <h3>{selectedKey}</h3>
            {selectedItems.length === 0 && <p className="empty">No maintenance that day.</p>}
            {selectedItems.map((it) => (
              <p key={it.id}>
                <strong>{it.title}</strong> · {it.estimated_minutes} min · {it.status}
                {it.assignee_name ? ` · ${it.assignee_name}` : ""}
              </p>
            ))}
          </>
        ) : (
          <p className="empty">Pick a day to see the forecast.</p>
        )}
      </div>
    </section>
  );
}

function Tasks({ user }) {
  const [tasks, setTasks] = useState([]);
  const [users, setUsers] = useState([]);
  const [err, setErr] = useState("");
  const canMutate = user.role !== "viewer";
  const [form, setForm] = useState({
    title: "",
    estimated_minutes: 30,
    recurrence: "monthly",
    season: "",
    day: 1,
    outdoor: false,
    require_dry: true,
    default_assignee_id: user.id,
  });

  async function load() {
    const [t, u] = await Promise.all([api("/api/tasks"), api("/api/users")]);
    setTasks(t);
    setUsers(u);
  }
  useEffect(() => {
    load().catch((e) => setErr(e.message));
  }, []);

  async function create(e) {
    e.preventDefault();
    setErr("");
    try {
      await api("/api/tasks", {
        method: "POST",
        body: {
          title: form.title,
          estimated_minutes: Number(form.estimated_minutes),
          recurrence: form.recurrence,
          season: form.season || null,
          day: Number(form.day) || null,
          weather_prefs: form.outdoor
            ? { outdoor: true, require_dry: form.require_dry, max_precip_mm: 0.8, min_temp_c: 4 }
            : { outdoor: false },
          default_assignee_id: Number(form.default_assignee_id) || null,
          conditions: form.outdoor ? ["weather-sensitive"] : [],
        },
      });
      setForm({ ...form, title: "" });
      await load();
    } catch (ex) {
      setErr(ex.message);
    }
  }

  return (
    <section className="split">
      <div>
        <h2>Catalog</h2>
        {err && <p className="error">{err}</p>}
        <ul className="catalog">
          {tasks.map((t) => (
            <li key={t.id}>
              <strong>{t.title}</strong>
              <span>
                {t.recurrence}
                {t.season ? `/${t.season}` : ""} · {t.estimated_minutes} min
                {t.weather_prefs?.outdoor ? " · outdoor" : " · indoor"}
                {t.depends_on_id ? ` · depends on #${t.depends_on_id}` : ""}
              </span>
            </li>
          ))}
        </ul>
      </div>
      {canMutate && (
        <form className="card" onSubmit={create}>
          <h2>Add task</h2>
          <label>
            Title
            <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
          </label>
          <label>
            Estimate (min)
            <input
              type="number"
              value={form.estimated_minutes}
              onChange={(e) => setForm({ ...form, estimated_minutes: e.target.value })}
            />
          </label>
          <label>
            Recurrence
            <select value={form.recurrence} onChange={(e) => setForm({ ...form, recurrence: e.target.value })}>
              <option>once</option>
              <option>monthly</option>
              <option>quarterly</option>
              <option>seasonal</option>
              <option>yearly</option>
            </select>
          </label>
          <label>
            Season
            <select value={form.season} onChange={(e) => setForm({ ...form, season: e.target.value })}>
              <option value="">—</option>
              <option>spring</option>
              <option>summer</option>
              <option>fall</option>
              <option>winter</option>
            </select>
          </label>
          <label>
            Assignee
            <select
              value={form.default_assignee_id}
              onChange={(e) => setForm({ ...form, default_assignee_id: e.target.value })}
            >
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name}
                </option>
              ))}
            </select>
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={form.outdoor}
              onChange={(e) => setForm({ ...form, outdoor: e.target.checked })}
            />
            Outdoor / weather-sensitive
          </label>
          <button type="submit">Create</button>
        </form>
      )}
    </section>
  );
}

function People({ user }) {
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "member" });
  const [err, setErr] = useState("");
  const load = () => api("/api/users").then(setUsers);
  useEffect(() => {
    load();
  }, []);

  async function create(e) {
    e.preventDefault();
    setErr("");
    try {
      await api("/api/users", { method: "POST", body: form });
      setForm({ name: "", email: "", password: "", role: "member" });
      await load();
    } catch (ex) {
      setErr(ex.message);
    }
  }

  return (
    <section className="split">
      <ul className="catalog">
        {users.map((u) => (
          <li key={u.id}>
            <strong>{u.name}</strong>
            <span>
              {u.email} · {u.role}
            </span>
          </li>
        ))}
      </ul>
      {user.role === "admin" && (
        <form className="card" onSubmit={create}>
          <h2>Add household member</h2>
          {err && <p className="error">{err}</p>}
          <label>
            Name
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </label>
          <label>
            Email
            <input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          </label>
          <label>
            Password
            <input
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required
            />
          </label>
          <label>
            Role
            <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
              <option>admin</option>
              <option>member</option>
              <option>viewer</option>
            </select>
          </label>
          <button type="submit">Add</button>
        </form>
      )}
    </section>
  );
}

function Weather({ house, user }) {
  const [forecast, setForecast] = useState(null);
  const [result, setResult] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    api("/api/weather/forecast")
      .then(setForecast)
      .catch((e) => setErr(e.message));
  }, []);

  async function run() {
    setErr("");
    try {
      const r = await api("/api/weather/reschedule", { method: "POST" });
      setResult(r);
    } catch (e) {
      setErr(e.message);
    }
  }

  return (
    <section>
      <p className="lede">
        Feed: Open-Meteo for {house?.address || "1944 Dinius"} ({house?.lat}, {house?.lon}). Outdoor tasks
        shift ±3 days when the scheduled day fails dry/temp/wind prefs.
      </p>
      {err && <p className="error">{err}</p>}
      {user.role !== "viewer" && (
        <button data-testid="weather-reschedule" onClick={run}>
          Reschedule from forecast
        </button>
      )}
      {result && <p>{result.checked} checked, {result.moved.length} moved.</p>}
      <div className="forecast">
        {(forecast?.days || []).map((d) => (
          <div key={d.date} className={`wx ${d.favorable_sample ? "ok" : "wet"}`}>
            <strong>{d.date.slice(5)}</strong>
            <span>{d.temp_max_c}°C</span>
            <span>{d.precip_mm} mm</span>
            <span>{d.wind_kmh} km/h</span>
          </div>
        ))}
      </div>
    </section>
  );
}
