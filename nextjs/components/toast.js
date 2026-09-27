export function Toast({ message, kind = "success" }) {
  if (!message) return null;
  return (
    <div className={`toast toast-${kind}`} role={kind === "error" ? "alert" : "status"} aria-live="polite">
      <span className="toast-dot" />{message}
    </div>
  );
}