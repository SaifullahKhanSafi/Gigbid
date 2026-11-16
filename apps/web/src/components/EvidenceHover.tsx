export type Evidence = {
  id: string;
  title?: string;
  text: string;
  source?: string;
  synthetic?: boolean;
  skills?: string[];
};
export function EvidenceHover({ item }: { item: Evidence }) {
  return (
    <details className="evidence">
      <summary>
        {item.title || item.id}
        <span>View source ↗</span>
      </summary>
      <p>{item.text}</p>
      <small>
        {item.source} ·{" "}
        {item.synthetic
          ? "Synthetic development evidence"
          : "User-supplied evidence"}
      </small>
    </details>
  );
}
