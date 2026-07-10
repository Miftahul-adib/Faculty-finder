import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { apiPost } from "../api.js";
import Avatar from "../components/Avatar.jsx";

const NAME_RE = /^[a-zA-Z\s]{2,50}$/;
const EMAIL_RE = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

const FEATURES = [
  { icon: "💬", title: "Ask in plain language", desc: "No filters or dropdowns — just describe the research area you're interested in." },
  { icon: "🎯", title: "AI-ranked matches", desc: "Semantic search surfaces the professors and peers most relevant to your query." },
  { icon: "🔖", title: "Save & organize", desc: "Bookmark professors and researchers, tag your own interests, and build your network." },
];

const DASHBOARD_CARDS = [
  { icon: "🔍", title: "Search Faculty", desc: "Ask in natural language — AI matches you with the right professors for supervision or collaboration.", to: "/search-faculty" },
  { icon: "👥", title: "Search PhD Students", desc: "Find PhD researchers by topic, method, or collaboration tag. Connect with peers.", to: "/search-phd" },
  { icon: "👤", title: "My Profile", desc: "Manage saved professors and researchers, post your works, and set collaboration tags.", to: "/profile" },
];

function LoggedInHome() {
  const { studentName } = useAuth();

  return (
    <div className="page fade-in">
      <div className="dashboard-hero">
        <Avatar name={studentName} size="lg" />
        <div className="profile-name" style={{ marginTop: "0.9rem" }}>
          {studentName}
        </div>
        <div className="profile-meta">Welcome back — pick where you'd like to go</div>
      </div>

      <div className="feature-grid">
        {DASHBOARD_CARDS.map((c) => (
          <Link key={c.to} to={c.to} className="feature-card">
            <div className="icon-chip">{c.icon}</div>
            <div className="title">{c.title}</div>
            <div className="desc">{c.desc}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}

function LoginForm() {
  const { login } = useAuth();
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (!email || !password) {
      setError("Please fill in both fields.");
      return;
    }
    setBusy(true);
    try {
      const data = await apiPost("/auth/login", { email, password });
      login(data);
      toast.success(`Welcome back, ${data.name}!`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit}>
      <div className="field">
        <label>Email address</label>
        <input
          type="email"
          name="login-email"
          autoComplete="username"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </div>
      <div className="field">
        <label>Password</label>
        <input
          type="password"
          name="login-password"
          autoComplete="current-password"
          placeholder="••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      <button className="btn btn-primary btn-block" type="submit" disabled={busy}>
        {busy ? "Logging in…" : "Log in"}
      </button>
    </form>
  );
}

function SignupForm({ onDone }) {
  const toast = useToast();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [university, setUniversity] = useState("SUST");
  const [department, setDepartment] = useState("");
  const [year, setYear] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (!name || !email || !password) {
      setError("Name, email and password are required.");
      return;
    }
    if (!NAME_RE.test(name.trim())) {
      setError("Full name can only contain letters and spaces (2-50 characters).");
      return;
    }
    if (!EMAIL_RE.test(email.trim())) {
      setError("Please enter a valid email address (e.g. name@sust.edu).");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    setBusy(true);
    try {
      await apiPost("/auth/signup", { name, email, password, university, department, year });
      toast.success("Account created! Switching to log in…");
      onDone();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit}>
      <div className="field">
        <label>Full name</label>
        <input
          name="signup-name"
          autoComplete="name"
          placeholder="e.g. Rafiul Islam"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </div>
      <div className="field">
        <label>Email address</label>
        <input
          type="email"
          name="signup-email"
          autoComplete="email"
          placeholder="you@sust.edu"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </div>
      <div className="field">
        <label>Password</label>
        <input
          type="password"
          name="signup-password"
          autoComplete="new-password"
          placeholder="Minimum 6 characters"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>
      <div className="field-row">
        <div className="field">
          <label>University</label>
          <input value={university} onChange={(e) => setUniversity(e.target.value)} />
        </div>
        <div className="field">
          <label>Department</label>
          <input placeholder="e.g. CSE" value={department} onChange={(e) => setDepartment(e.target.value)} />
        </div>
      </div>
      <div className="field">
        <label>Year / Status</label>
        <select value={year} onChange={(e) => setYear(e.target.value)}>
          {["", "1st Year", "2nd Year", "3rd Year", "4th Year", "Masters", "PhD Student", "Graduate"].map((y) => (
            <option key={y} value={y}>
              {y || "Select…"}
            </option>
          ))}
        </select>
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      <button className="btn btn-primary btn-block" type="submit" disabled={busy}>
        {busy ? "Creating account…" : "Create account"}
      </button>
    </form>
  );
}

function LandingHome() {
  const [tab, setTab] = useState("login");

  return (
    <div className="page fade-in">
      <div className="landing-hero">
        <div className="landing-badge">🔬 AI-powered research matchmaking</div>
        <h1 className="landing-title">
          Find your next
          <br />
          <span className="accent-word">research connection</span>
        </h1>
        <p className="landing-subtitle">
          ScholarLink pairs you with the professors, PhD researchers, and collaborators who match your interests —
          described in plain language, not keyword search.
        </p>
        <div className="landing-stats">
          <div>
            <div className="landing-stat-num">611+</div>
            <div className="landing-stat-label">FACULTY PROFILES</div>
          </div>
          <div>
            <div className="landing-stat-num">AI</div>
            <div className="landing-stat-label">SEMANTIC MATCHING</div>
          </div>
          <div>
            <div className="landing-stat-num">SUST</div>
            <div className="landing-stat-label">CAMPUS NETWORK</div>
          </div>
        </div>
      </div>

      <div className="auth-panel">
        <div className="tabs">
          <button className={`tab ${tab === "login" ? "active" : ""}`} onClick={() => setTab("login")}>
            Log in
          </button>
          <button className={`tab ${tab === "signup" ? "active" : ""}`} onClick={() => setTab("signup")}>
            Sign up
          </button>
        </div>
        <div className="tab-panel">
          {tab === "login" ? <LoginForm /> : <SignupForm onDone={() => setTab("login")} />}
        </div>
      </div>

      <hr className="divider" />

      <div className="feature-grid">
        {FEATURES.map((f) => (
          <div key={f.title} className="feature-card">
            <div className="icon-chip">{f.icon}</div>
            <div className="title">{f.title}</div>
            <div className="desc">{f.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Home() {
  const { isLoggedIn } = useAuth();
  return isLoggedIn ? <LoggedInHome /> : <LandingHome />;
}
