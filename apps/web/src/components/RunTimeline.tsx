export function RunTimeline({ events }: { events: Record<string, unknown>[] }) {
  return (
    <ol className="timeline">
      {events.map((e, i) => (
        <li key={i}>
          <span className="timeline-dot" />
          <div>
            <strong>{String(e.node || "step").replaceAll("_", " ")}</strong>
            <small>
              {e.seconds ? `${Number(e.seconds).toFixed(2)}s` : "Completed"}
              {e.usage && typeof e.usage === "object"
                ? ` · ${String((e.usage as Record<string, unknown>).model || "rules")}`
                : ""}
            </small>
          </div>
          <span className="badge green">Complete</span>
        </li>
      ))}
    </ol>
  );
}
