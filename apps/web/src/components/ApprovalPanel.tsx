import { useState } from "react";
import { Check, X, Save } from "lucide-react";
import type { Approval } from "../lib/api/client";
export function ApprovalPanel({
  pending,
  changed,
  preview,
  onAction,
  kind = "proposal",
}: {
  kind?: "proposal" | "message";
  pending: boolean;
  changed: boolean;
  preview: Record<string, unknown>;
  onAction: (a: Approval) => Promise<void>;
}) {
  const [reason, setReason] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function act(action: Approval["action"]) {
    setBusy(true);
    setError("");
    try {
      await onAction({ action, reason });
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="approval">
      <div>
        <span className="eyebrow">YOU HAVE THE FINAL SAY</span>
        <h3>Review before it leaves</h3>
        <p>
          Review this exact draft and its reported cost. Unknown live costs must
          be confirmed on the platform. Your edits go through the checks again.
        </p>
      </div>
      <div className="preview-cost">
        <strong>
          {preview.connects_cost == null ? "—" : String(preview.connects_cost)}
        </strong>
        <span>
          {preview.connects_cost == null ? "Confirm on platform" : "Connects"}
        </span>
      </div>
      <details className="preview-json">
        <summary>Inspect dry-run preview</summary>
        <pre>{JSON.stringify(preview, null, 2)}</pre>
      </details>
      <label className="reason">
        Rejection reason
        <input
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Tell the agent what to improve"
        />
      </label>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <div className="button-row">
        <button
          className="primary"
          disabled={!pending || busy}
          onClick={() => act(changed ? "edit" : "approve")}
        >
          {changed ? <Save size={16} /> : <Check size={16} />}{" "}
          {changed
            ? "Save edits & recheck"
            : kind === "message"
              ? "Approve message"
              : "Approve proposal"}
        </button>
        <button
          className="secondary danger"
          disabled={!pending || busy || !reason.trim()}
          onClick={() => act("reject")}
        >
          <X size={16} /> Reject with reason
        </button>
      </div>
    </section>
  );
}
