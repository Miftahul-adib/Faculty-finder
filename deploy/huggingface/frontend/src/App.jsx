import { useState } from "react";
import { Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar.jsx";
import MeshBackground from "./components/MeshBackground.jsx";
import Home from "./pages/Home.jsx";
import SearchFaculty from "./pages/SearchFaculty.jsx";
import SearchPhd from "./pages/SearchPhd.jsx";
import Profile from "./pages/Profile.jsx";

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="app-shell">
      <MeshBackground />
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="app-main">
        <header className="topbar">
          <button className="icon-btn" onClick={() => setSidebarOpen(true)} aria-label="Open menu">
            ☰
          </button>
          <strong>ScholarLink</strong>
          <span style={{ width: 38 }} />
        </header>

        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/search-faculty" element={<SearchFaculty />} />
          <Route path="/search-phd" element={<SearchPhd />} />
          <Route path="/profile" element={<Profile />} />
        </Routes>
      </div>
    </div>
  );
}
