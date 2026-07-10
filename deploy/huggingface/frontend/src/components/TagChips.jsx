export default function TagChips({ tags, light = false }) {
  if (!tags || tags.length === 0) return null;
  return (
    <div className="tag-row">
      {tags.map((t, i) => (
        <span key={i} className={`tag-chip ${light ? "tag-chip-light" : ""}`}>
          {t}
        </span>
      ))}
    </div>
  );
}
