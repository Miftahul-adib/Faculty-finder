import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { useTheme } from "../context/ThemeContext.jsx";
import Avatar from "./Avatar.jsx";
import logo from "../assets/logo_icon.svg";

const NAV = [
  { to: "/", label: "Home", emoji: "🏠" },
  { to: "/search-faculty", label: "Search Faculty", emoji: "🔍" },
  { to: "/search-phd", label: "Search PhD Students", emoji: "👥" },
  { to: "/profile", label: "My Profile", emoji: "👤" },
];

export default function Sidebar({ open, onClose }) {
  const { isLoggedIn, studentName, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  return (
    <>
      <div className={`sidebar-backdrop ${open ? "open" : ""}`} onClick={onClose} />
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <div className="sidebar-brand">
          <img src={logo} alt="ScholarLink" />
          <div>
            <div className="name">ScholarLink</div>
            <div className="tagline">Research Matchmaking</div>
          </div>
        </div>

        <nav className="sidebar-nav">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) => `sidebar-link ${isActive ? "active" : ""}`}
              onClick={onClose}
            >
              <span className="emoji">{item.emoji}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <button className="theme-toggle" onClick={toggleTheme}>
            <span>{theme === "dark" ? "🌙 Dark mode" : "☀️ Light mode"}</span>
            <span>{theme === "dark" ? "→ ☀️" : "→ 🌙"}</span>
          </button>

          {isLoggedIn && (
            <>
              <div className="sidebar-user">
                <Avatar name={studentName} size="sm" />
                <div className="info">
                  <div className="name">{studentName}</div>
                  <div className="email">Logged in</div>
                </div>
              </div>
              <button className="btn btn-ghost btn-sm btn-block" onClick={logout}>
                Log out
              </button>
            </>
          )}
        </div>
      </aside>
    </>
  );
}
