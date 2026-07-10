import { useEffect, useRef, useState } from "react";
import { apiDelete, apiGet, apiPost, streamQuery } from "../api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import Avatar from "../components/Avatar.jsx";
import SectionLabel from "../components/SectionLabel.jsx";
import TagChips from "../components/TagChips.jsx";
import ChatMarkdown from "../components/ChatMarkdown.jsx";

const SUGGESTIONS = [
  "Find a research partner working on NLP or Bangla text processing",
  "PhD students working on medical image analysis",
  "Who is open to collaboration in computer vision?",
];

function CandidateCard({ c, saved, onToggleSave, isLoggedIn }) {
  const tagsTxt = (c.tags || []).map((t) => (typeof t === "string" ? t : t.tag));
  const metaParts = [c.department, c.supervisor ? `Sup: ${c.supervisor}` : ""].filter(Boolean);
  const research = c.research_area || "";

  return (
    <div className="candidate-row">
      <div className="dark-card">
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Avatar name={c.name} size="sm" />
          <div>
            <div className="name">{c.name}</div>
            <div className="meta">{metaParts.join(" · ")}</div>
          </div>
        </div>
        {research && (
          <div className="research">
            {research.slice(0, 220)}
            {research.length > 220 ? "…" : ""}
          </div>
        )}
        {c.email && <div className="email">{c.email}</div>}
        <TagChips tags={tagsTxt} />
      </div>
      <div className="save-slot">
        {isLoggedIn ? (
          <button
            className={`btn btn-sm ${saved ? "btn-ghost" : "btn-primary"} btn-block`}
            onClick={onToggleSave}
          >
            {saved ? "✓ Saved" : "+ Save"}
          </button>
        ) : (
          <span style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>Log in to save</span>
        )}
      </div>
    </div>
  );
}

export default function SearchPhd() {
  const { isLoggedIn, studentId } = useAuth();
  const toast = useToast();
  const [messages, setMessages] = useState([]);
  const [candidates, setCandidates] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [savedPhdIds, setSavedPhdIds] = useState(new Set());
  const [savedStudentIds, setSavedStudentIds] = useState(new Set());
  const bottomRef = useRef(null);

  useEffect(() => {
    if (!isLoggedIn) return;
    apiGet(`/student/${studentId}/saved-phd`)
      .then((rows) => setSavedPhdIds(new Set(rows.map((p) => p.id))))
      .catch(() => {});
    apiGet(`/student/${studentId}/saved-students`)
      .then((rows) => setSavedStudentIds(new Set(rows.map((p) => p.id))))
      .catch(() => {});
  }, [isLoggedIn, studentId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  const isSaved = (c) => (c.source === "phd" ? savedPhdIds.has(c.id) : savedStudentIds.has(c.id));

  const toggleSave = async (c) => {
    const saved = isSaved(c);
    try {
      if (c.source === "phd") {
        if (saved) {
          await apiDelete(`/student/${studentId}/save-phd/${c.id}`);
          setSavedPhdIds((s) => new Set([...s].filter((x) => x !== c.id)));
        } else {
          await apiPost(`/student/${studentId}/save-phd`, { phd_student_id: c.id });
          setSavedPhdIds((s) => new Set(s).add(c.id));
        }
      } else {
        if (saved) {
          await apiDelete(`/student/${studentId}/save-student/${c.id}`);
          setSavedStudentIds((s) => new Set([...s].filter((x) => x !== c.id)));
        } else {
          await apiPost(`/student/${studentId}/save-student`, { target_student_id: c.id });
          setSavedStudentIds((s) => new Set(s).add(c.id));
        }
      }
    } catch (err) {
      toast.error(err.message);
    }
  };

  const send = (text) => {
    const query = text.trim();
    if (!query || streaming) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: query }, { role: "assistant", content: "" }]);
    setCandidates([]);
    setStreaming(true);

    streamQuery("/ask-phd-stream", query, {
      onToken: (tok) => {
        setMessages((m) => {
          const next = [...m];
          next[next.length - 1] = { role: "assistant", content: next[next.length - 1].content + tok };
          return next;
        });
      },
      onDone: (cands) => {
        setCandidates(cands);
        setStreaming(false);
      },
      onError: (err) => {
        setMessages((m) => {
          const next = [...m];
          next[next.length - 1] = { role: "assistant", content: `Connection error: ${err.message}` };
          return next;
        });
        setStreaming(false);
      },
    });
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  };

  return (
    <div className="page fade-in">
      <div className="page-hero">
        <h1 className="page-title">Search PhD Students</h1>
        <div className="page-title-accent" />
        <p className="page-subtitle">Describe your research interest or collaboration goal — we'll find the right researchers</p>
      </div>

      <div className="info-banner">
        <p>— Ask in natural language, just like the faculty search. The AI understands context.</p>
        <p>
          — Try: <em>"Find a research partner working on NLP or Bangla text processing"</em>
        </p>
        <p>— Results include PhD researchers and registered students with matching collaboration tags.</p>
      </div>

      {messages.length === 0 && (
        <div className="chat-empty">
          <div className="icon">👥</div>
          <div>Ask about a research area or collaboration goal</div>
          <div className="suggested-chip-row" style={{ justifyContent: "center" }}>
            {SUGGESTIONS.map((s) => (
              <button key={s} className="suggested-chip" onClick={() => send(s)}>
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="chat-thread">
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}`}>
            {m.role === "user" ? (
              <div className="chat-bubble-user">{m.content}</div>
            ) : (
              <div className="chat-bubble-assistant">
                {m.content ? (
                  <ChatMarkdown content={m.content} />
                ) : streaming && i === messages.length - 1 ? (
                  <span className="typing-dots">
                    <span></span><span></span><span></span>
                  </span>
                ) : null}
              </div>
            )}
          </div>
        ))}
        {candidates.length > 0 && !streaming && (
          <div>
            <SectionLabel>{candidates.length} top matches — save to your list</SectionLabel>
            {candidates.map((c) => (
              <CandidateCard
                key={`${c.source}_${c.id}`}
                c={c}
                saved={isSaved(c)}
                onToggleSave={() => toggleSave(c)}
                isLoggedIn={isLoggedIn}
              />
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-bar">
        <div className="chat-input-shell">
          <textarea
            rows={1}
            placeholder="e.g. Find a research partner working on medical image analysis"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
          />
          <button className="chat-send-btn" onClick={() => send(input)} disabled={streaming || !input.trim()}>
            ➤
          </button>
        </div>
      </div>
    </div>
  );
}
