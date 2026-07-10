import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiDelete, apiGet, apiPost, apiPut } from "../api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import Avatar from "../components/Avatar.jsx";
import SectionLabel from "../components/SectionLabel.jsx";
import TagChips from "../components/TagChips.jsx";

const SUGGESTED_TAGS = [
  "Looking for research partner in ML",
  "Looking for research partner in NLP",
  "Looking for research partner in Computer Vision",
  "Looking for research partner in Bioinformatics",
  "Looking for research partner in IoT",
  "Open to research collaboration",
  "Looking for co-author",
  "Seeking PhD supervisor",
  "Available for project collaboration",
  "Looking for industry partner",
  "Open to internship opportunities",
  "Seeking thesis partner",
];

const TABS = [
  { key: "edit", label: "✏️ Edit Profile" },
  { key: "posts", label: "📝 Posts" },
  { key: "tags", label: "🏷️ Tags" },
  { key: "saved", label: "🔖 Saved" },
];

function EditTab({ profile, sid, onUpdated }) {
  const toast = useToast();
  const [bio, setBio] = useState(profile.bio || "");
  const [university, setUniversity] = useState(profile.university || "SUST");
  const [department, setDepartment] = useState(profile.department || "");
  const [year, setYear] = useState(profile.year || "");
  const [researchInterests, setResearchInterests] = useState(profile.research_interests || "");
  const [researchSummary, setResearchSummary] = useState(profile.research_summary || "");
  const [certifications, setCertifications] = useState(profile.certifications || "");
  const [cvFile, setCvFile] = useState(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await apiPut(`/student/${sid}`, {
        bio,
        university,
        department,
        year,
        research_interests: researchInterests,
        research_summary: researchSummary,
        certifications,
        cv_path: cvFile ? cvFile.name : profile.cv_path,
      });
      toast.success("Profile updated successfully!");
      onUpdated();
    } catch (err) {
      toast.error(`Failed to update profile: ${err.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit}>
      <SectionLabel>Update your profile</SectionLabel>
      <div className="field">
        <label>Bio / About me</label>
        <textarea
          style={{ minHeight: 110 }}
          placeholder="Describe your research interests, background, and collaboration goals…"
          value={bio}
          onChange={(e) => setBio(e.target.value)}
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
        <input value={year} onChange={(e) => setYear(e.target.value)} />
      </div>

      <h3 style={{ margin: "1.2rem 0 0.8rem", fontSize: "1rem" }}>Research Details</h3>

      <div className="field">
        <label>Research Interests</label>
        <textarea
          placeholder="e.g. Machine Learning, NLP, Computer Vision, Bioinformatics"
          value={researchInterests}
          onChange={(e) => setResearchInterests(e.target.value)}
        />
      </div>
      <div className="field">
        <label>Research Summary / Thesis Focus</label>
        <textarea
          placeholder="Brief summary of your current research work, thesis topic, or key projects…"
          value={researchSummary}
          onChange={(e) => setResearchSummary(e.target.value)}
        />
      </div>
      <div className="field">
        <label>Certifications & Achievements</label>
        <textarea
          placeholder="e.g. AWS Certified, Published papers, Awards, Completed courses…"
          value={certifications}
          onChange={(e) => setCertifications(e.target.value)}
        />
      </div>
      <div className="field">
        <label>Upload CV (PDF)</label>
        <label className="file-drop">
          {cvFile ? cvFile.name : profile.cv_path ? `Current: ${profile.cv_path}` : "Click to choose a PDF file"}
          <input
            type="file"
            accept="application/pdf"
            style={{ display: "none" }}
            onChange={(e) => setCvFile(e.target.files?.[0] || null)}
          />
        </label>
      </div>

      <button className="btn btn-primary btn-block" type="submit" disabled={busy}>
        {busy ? "Saving…" : "Save changes"}
      </button>
    </form>
  );
}

function PostsTab({ profile, sid, onUpdated }) {
  const toast = useToast();
  const [postType, setPostType] = useState("work");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!title.trim()) {
      toast.error("Title is required.");
      return;
    }
    setBusy(true);
    try {
      await apiPost(`/student/${sid}/posts`, { title: title.trim(), content: content.trim(), post_type: postType });
      toast.success("Post published!");
      setTitle("");
      setContent("");
      onUpdated();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setBusy(false);
    }
  };

  const removePost = async (id) => {
    await apiDelete(`/student/${sid}/posts/${id}`);
    onUpdated();
  };

  const posts = profile.posts || [];

  return (
    <div>
      <SectionLabel>Add a post</SectionLabel>
      <form onSubmit={submit}>
        <div className="field">
          <label>Type</label>
          <select value={postType} onChange={(e) => setPostType(e.target.value)}>
            <option value="work">Work / Project</option>
            <option value="interest">Research Interest</option>
          </select>
        </div>
        <div className="field">
          <label>Title</label>
          <input placeholder="e.g. Paper on Bangla NLP tokenisation" value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div className="field">
          <label>Details (optional)</label>
          <textarea
            placeholder="Describe what you did, what methods you used, what you found…"
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
        </div>
        <button className="btn btn-primary btn-block" type="submit" disabled={busy}>
          Publish post
        </button>
      </form>

      <hr className="divider" />

      {posts.length === 0 && <div className="empty-state">No posts yet. Share your work or research interests above.</div>}
      {posts.map((post) => (
        <div key={post.id} className="row-with-action">
          <div className="post-card">
            <div className="post-type-badge">{post.post_type === "work" ? "Work / Project" : "Research Interest"}</div>
            <div className="post-title">{post.title}</div>
            {post.content && <div className="post-content">{post.content}</div>}
            <div className="post-date">{post.created_at?.slice(0, 10)}</div>
          </div>
          <button className="btn-danger-ghost" onClick={() => removePost(post.id)} title="Delete post">
            ✕
          </button>
        </div>
      ))}
    </div>
  );
}

function TagsTab({ profile, sid, onUpdated }) {
  const toast = useToast();
  const [custom, setCustom] = useState("");
  const existingTags = profile.tags || [];
  const used = new Set(existingTags.map((t) => t.tag));

  const addTag = async (tag) => {
    await apiPost(`/student/${sid}/tags`, { tag });
    onUpdated();
  };

  const removeTag = async (id) => {
    await apiDelete(`/student/${sid}/tags/${id}`);
    onUpdated();
  };

  const submitCustom = async (e) => {
    e.preventDefault();
    const t = custom.trim();
    if (!t) {
      toast.error("Tag cannot be empty.");
      return;
    }
    if (used.has(t)) {
      toast.info("You already have this tag.");
      return;
    }
    await addTag(t);
    setCustom("");
  };

  return (
    <div>
      <div className="info-banner">
        <p>
          Tags appear as colored chips behind your name when others search for PhD students and researchers. They
          signal what kind of collaboration you are open to.
        </p>
      </div>

      <SectionLabel>Quick-add suggested tags</SectionLabel>
      <div className="tag-suggest-grid">
        {SUGGESTED_TAGS.map((tag) =>
          used.has(tag) ? (
            <span key={tag} className="tag-chip is-used">
              {tag} ✓
            </span>
          ) : (
            <button key={tag} className="btn btn-ghost btn-sm" onClick={() => addTag(tag)}>
              + {tag}
            </button>
          )
        )}
      </div>

      <hr className="divider" />
      <SectionLabel>Add a custom tag</SectionLabel>
      <form onSubmit={submitCustom} style={{ display: "flex", gap: "0.6rem" }}>
        <input
          style={{
            flex: 1,
            background: "var(--surface-2)",
            border: "1.5px solid var(--border)",
            borderRadius: "var(--radius-sm)",
            color: "var(--text)",
            padding: "0.65rem 0.85rem",
            minHeight: 44,
          }}
          placeholder="e.g. Looking for partner in quantum ML"
          value={custom}
          onChange={(e) => setCustom(e.target.value)}
        />
        <button className="btn btn-primary" type="submit">
          Add tag
        </button>
      </form>

      {existingTags.length > 0 && (
        <>
          <hr className="divider" />
          <SectionLabel>Your current tags</SectionLabel>
          {existingTags.map((t) => (
            <div key={t.id} className="row-with-action" style={{ alignItems: "center", marginBottom: "0.5rem" }}>
              <TagChips tags={[t.tag]} />
              <button className="btn-danger-ghost" onClick={() => removeTag(t.id)} title="Remove tag">
                ✕
              </button>
            </div>
          ))}
        </>
      )}
    </div>
  );
}

function SavedList({ title, items, empty, renderItem, onRemove }) {
  return (
    <div>
      <SectionLabel>{title}</SectionLabel>
      {items.length === 0 && <div className="empty-state">{empty}</div>}
      {items.map((item) => (
        <div key={item.id} className="row-with-action" style={{ marginBottom: "0.7rem" }}>
          <div className="match-card">
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <Avatar name={item.name} size="sm" />
              <div>
                <div className="name">{item.name}</div>
                <div className="meta">{renderItem.meta(item)}</div>
              </div>
            </div>
            {renderItem.extra?.(item)}
          </div>
          <button className="btn-danger-ghost" onClick={() => onRemove(item.id)} title="Remove">
            ✕
          </button>
        </div>
      ))}
    </div>
  );
}

function SavedTab({ sid }) {
  const [savedFaculty, setSavedFaculty] = useState([]);
  const [savedPhd, setSavedPhd] = useState([]);
  const [savedStudents, setSavedStudents] = useState([]);

  const load = () => {
    apiGet(`/student/${sid}/saved-faculty`).then(setSavedFaculty).catch(() => {});
    apiGet(`/student/${sid}/saved-phd`).then(setSavedPhd).catch(() => {});
    apiGet(`/student/${sid}/saved-students`).then(setSavedStudents).catch(() => {});
  };

  useEffect(load, [sid]);

  return (
    <div>
      <SavedList
        title="Saved Professors"
        items={savedFaculty}
        empty="No saved professors yet. Use Search Faculty and click + Save."
        renderItem={{ meta: (f) => [f.designation, f.department].filter(Boolean).join(" · ") }}
        onRemove={async (id) => {
          await apiDelete(`/student/${sid}/save-faculty/${id}`);
          load();
        }}
      />
      <hr className="divider" />
      <SavedList
        title="Saved PhD Researchers"
        items={savedPhd}
        empty="No saved PhD researchers yet. Use Search PhD Students and click + Save."
        renderItem={{
          meta: (p) => [p.department, p.university, p.supervisor ? `Sup: ${p.supervisor}` : ""].filter(Boolean).join(" · "),
          extra: (p) =>
            p.research_area && (
              <div className="research" style={{ marginTop: 4 }}>
                {p.research_area.slice(0, 160)}
                {p.research_area.length > 160 ? "…" : ""}
              </div>
            ),
        }}
        onRemove={async (id) => {
          await apiDelete(`/student/${sid}/save-phd/${id}`);
          load();
        }}
      />
      <hr className="divider" />
      <SavedList
        title="Saved Students"
        items={savedStudents}
        empty="No saved students yet."
        renderItem={{
          meta: (s) => [s.department, s.university].filter(Boolean).join(" · "),
          extra: (s) => (
            <>
              {s.bio && (
                <div className="research" style={{ marginTop: 4 }}>
                  {s.bio.slice(0, 120)}…
                </div>
              )}
              <TagChips tags={s.tags} />
            </>
          ),
        }}
        onRemove={async (id) => {
          await apiDelete(`/student/${sid}/save-student/${id}`);
          load();
        }}
      />
    </div>
  );
}

export default function Profile() {
  const { isLoggedIn, studentId } = useAuth();
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("edit");

  const load = () => {
    apiGet(`/student/${studentId}`)
      .then(setProfile)
      .catch(() => setError("Could not load your profile. Please try again."));
  };

  useEffect(() => {
    if (isLoggedIn) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoggedIn, studentId]);

  if (!isLoggedIn) {
    return (
      <div className="page fade-in">
        <div className="profile-hero">
          <div className="lock-icon" style={{ fontSize: "2rem", marginBottom: "0.8rem" }}>🔒</div>
          <div className="profile-name">My Profile</div>
          <div className="profile-meta">Please log in to view your profile</div>
        </div>
        <div className="alert alert-success" style={{ textAlign: "center" }}>
          Go to the <Link to="/" style={{ textDecoration: "underline" }}>Home page</Link> to log in or sign up.
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page fade-in">
        <div className="alert alert-error">{error}</div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="page fade-in">
        <div className="spinner-row">
          <span className="spinner" /> Loading your profile…
        </div>
      </div>
    );
  }

  const tagTexts = (profile.tags || []).map((t) => t.tag);
  const metaParts = [profile.department, profile.university].filter(Boolean);
  if (profile.year) metaParts.push(profile.year);

  return (
    <div className="page fade-in">
      <div className="profile-hero">
        <Avatar name={profile.name} size="lg" />
        <div className="profile-name" style={{ marginTop: "0.9rem" }}>{profile.name}</div>
        <div className="profile-meta">{metaParts.join(" · ")}</div>
        {tagTexts.length > 0 && (
          <div style={{ marginTop: "0.8rem", display: "flex", justifyContent: "center" }}>
            <TagChips tags={tagTexts} />
          </div>
        )}
      </div>

      <div className="tabs">
        {TABS.map((t) => (
          <button key={t.key} className={`tab ${tab === t.key ? "active" : ""}`} onClick={() => setTab(t.key)}>
            {t.label}
          </button>
        ))}
      </div>

      <div className="tab-panel">
        {tab === "edit" && <EditTab profile={profile} sid={studentId} onUpdated={load} />}
        {tab === "posts" && <PostsTab profile={profile} sid={studentId} onUpdated={load} />}
        {tab === "tags" && <TagsTab profile={profile} sid={studentId} onUpdated={load} />}
        {tab === "saved" && <SavedTab sid={studentId} />}
      </div>
    </div>
  );
}
