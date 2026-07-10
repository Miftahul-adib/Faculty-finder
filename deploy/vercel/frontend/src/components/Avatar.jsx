function getInitials(name) {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

export default function Avatar({ name, size = "md" }) {
  return (
    <div className={`avatar avatar-${size} icon-chip`} style={{ borderRadius: "50%" }}>
      {getInitials(name)}
    </div>
  );
}
