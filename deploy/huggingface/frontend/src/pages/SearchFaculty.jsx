import { useEffect, useRef, useState } from "react";
import { apiDelete, apiGet, apiPost, streamQuery } from "../api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import Avatar from "../components/Avatar.jsx";
import SectionLabel from "../components/SectionLabel.jsx";
import ChatMarkdown from "../components/ChatMarkdown.jsx";

const SUGGESTIONS = [
  "Find a PhD supervisor for deep learning in medical imaging",
  "Who works on flood prediction at SUST?",
  "Faculty researching natural language processing",
];

function CandidateCard({ c, saved, onToggleSave, isLoggedIn }) {
  const meta = [c.designation, c.department].filter(Boolean).join(" · ");
  return (
    <div className="candidate-row">
      <div className="dark-card">
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Avatar name={c.name} size="sm" />
          <div>
            <div className="name">{c.name}</div>
            <div className="meta">{meta}</div>
          </div>
        </div>
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

export default function SearchFaculty() {
  const { isLoggedIn, studentId } = useAuth();
  const toast = useToast();
  const [messages, setMessages] = useState([]);
  const [candidates, setCandidates] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [savedIds, setSavedIds] = useState(new Set());
  const bottomRef = useRef(null);

  useEffect(() => {
    if (!isLoggedIn) return;
    apiGet(`/student/${studentId}/saved-faculty`)
      .then((rows) => setSavedIds(new Set(rows.map((f) => f.id))))
      .catch(() => {});
  }, [isLoggedIn, studentId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  const toggleSave = async (fid) => {
    try {
      if (savedIds.has(fid)) {
        await apiDelete(`/student/${studentId}/save-faculty/${fid}`);
        setSavedIds((s) => new Set([...s].filter((x) => x !== fid)));
      } else {
        await apiPost(`/student/${studentId}/save-faculty`, { faculty_id: fid });
        setSavedIds((s) => new Set(s).add(fid));
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

    streamQuery("/ask-stream", query, {
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
        <h1 className="page-title">Search Faculty</h1>
        <div className="page-title-accent" />
        <p className="page-subtitle">Describe your research interest in plain language — our AI finds the right professors</p>
      </div>

      <div className="info-banner">
        <p>— Ask one question at a time. Each query is answered independently.</p>
        <p>
          — Try: <em>"Find me a PhD supervisor for deep learning in medical imaging"</em> or{" "}
          <em>"Who works on flood prediction at SUST?"</em>
        </p>
        <p>
          — <strong>Faculty database:</strong> SUST (611 faculty). More universities coming soon.
        </p>
      </div>

      {messages.length === 0 && (
        <div className="chat-empty">
          <div className="icon">🔍</div>
          <div>Ask about any research area to find matching faculty</div>
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
                key={c.id}
                c={c}
                saved={savedIds.has(c.id)}
                onToggleSave={() => toggleSave(c.id)}
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
            placeholder="e.g. Find a PhD supervisor for machine learning and NLP research"
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
