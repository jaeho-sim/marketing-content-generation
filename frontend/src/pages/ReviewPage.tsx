import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getDraftByEvent, getReview, addComment, submitDecision } from "@/api/drafts";

const REVIEWER_ID = "reviewer-demo";

export default function ReviewPage() {
  const { eventId } = useParams<{ eventId: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [body, setBody] = useState("");

  const { data: draft, isLoading } = useQuery({
    queryKey: ["draft", eventId],
    queryFn: () => getDraftByEvent(eventId!),
    enabled: !!eventId,
  });

  const { data: review } = useQuery({
    queryKey: ["review", draft?.id],
    queryFn: () => getReview(draft!.id),
    enabled: !!draft?.id,
  });

  const invalidateReview = () => qc.invalidateQueries({ queryKey: ["review", draft?.id] });

  const commentMutation = useMutation({
    mutationFn: () =>
      addComment(draft!.id, { author_id: REVIEWER_ID, author_role: "reviewer", body }),
    onSuccess: () => { setBody(""); invalidateReview(); },
  });

  const decisionMutation = useMutation({
    mutationFn: (decision: "approved" | "rejected") =>
      submitDecision(draft!.id, { reviewer_id: REVIEWER_ID, decision }),
    onSuccess: invalidateReview,
  });

  if (isLoading) return <div style={s.page}>Loading draft…</div>;
  if (!draft) return <div style={s.page}>Draft not available yet.</div>;

  const decided = !!review?.decision;

  return (
    <div style={s.page}>
      <button style={s.back} onClick={() => navigate(-1)}>← Back</button>
      <h1 style={s.heading}>Draft Review</h1>

      {review?.decision && (
        <div style={banner(review.decision)}>
          Decision: <strong>{review.decision.toUpperCase()}</strong>
          {review.decided_at && ` — ${new Date(review.decided_at).toLocaleString()}`}
        </div>
      )}

      <div style={s.card}>
        <h2 style={s.cardTitle}>Generated Draft</h2>
        <pre style={s.draft}>{draft.content}</pre>
        <p style={s.meta}>
          {draft.llm_model ?? draft.llm_provider} · {draft.prompt_tokens ?? "?"} in / {draft.completion_tokens ?? "?"} out tokens
        </p>
      </div>

      <div style={s.card}>
        <h2 style={s.cardTitle}>Comments</h2>
        {!review?.comments.length && <p style={s.hint}>No comments yet.</p>}
        {review?.comments.map((c) => (
          <div key={c.id} style={s.comment}>
            <div style={s.commentMeta}>
              <strong>{c.author_id}</strong>
              <span style={s.role}>{c.author_role}</span>
              <span style={s.date}>{new Date(c.created_at).toLocaleString()}</span>
            </div>
            <p style={s.commentBody}>{c.body}</p>
          </div>
        ))}
        {!decided && (
          <>
            <textarea
              style={s.textarea}
              rows={3}
              placeholder="Add a comment…"
              value={body}
              onChange={(e) => setBody(e.target.value)}
            />
            <button
              style={s.btnSecondary}
              disabled={!body || commentMutation.isPending}
              onClick={() => commentMutation.mutate()}
            >
              Post Comment
            </button>
          </>
        )}
      </div>

      {!decided && (
        <div style={s.card}>
          <h2 style={s.cardTitle}>Decision</h2>
          <div style={{ display: "flex", gap: 12 }}>
            <button
              style={s.btnApprove}
              disabled={decisionMutation.isPending}
              onClick={() => decisionMutation.mutate("approved")}
            >
              Approve
            </button>
            <button
              style={s.btnReject}
              disabled={decisionMutation.isPending}
              onClick={() => decisionMutation.mutate("rejected")}
            >
              Reject
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

const banner = (decision: string): React.CSSProperties => ({
  padding: "0.75rem 1rem",
  borderRadius: 8,
  marginBottom: "1rem",
  background: decision === "approved" ? "#dcfce7" : "#fee2e2",
  color: decision === "approved" ? "#166534" : "#991b1b",
  fontWeight: 500,
});

const s: Record<string, React.CSSProperties> = {
  page: { maxWidth: 720, margin: "0 auto", padding: "2rem 1rem", fontFamily: "system-ui, sans-serif" },
  back: { background: "none", border: "none", cursor: "pointer", color: "#1d4ed8", padding: 0, marginBottom: "1rem", fontSize: "0.9rem" },
  heading: { fontSize: "1.5rem", fontWeight: 700, margin: "0 0 1rem" },
  card: { background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, padding: "1.5rem", marginBottom: "1.25rem" },
  cardTitle: { fontSize: "1.05rem", fontWeight: 600, marginTop: 0, marginBottom: "0.75rem" },
  draft: { whiteSpace: "pre-wrap", wordBreak: "break-word", background: "#f9fafb", padding: "1rem", borderRadius: 6, fontSize: "0.88rem", lineHeight: 1.7, margin: 0 },
  meta: { fontSize: "0.75rem", color: "#9ca3af", marginTop: "0.5rem", marginBottom: 0 },
  hint: { color: "#9ca3af", fontSize: "0.875rem" },
  comment: { paddingBottom: "0.75rem", marginBottom: "0.75rem", borderBottom: "1px solid #f3f4f6" },
  commentMeta: { display: "flex", gap: 8, alignItems: "center", marginBottom: 4 },
  role: { fontSize: "0.7rem", padding: "1px 6px", background: "#e0e7ff", color: "#3730a3", borderRadius: 12, fontWeight: 700 },
  date: { fontSize: "0.75rem", color: "#9ca3af", marginLeft: "auto" },
  commentBody: { margin: 0, fontSize: "0.9rem", color: "#374151" },
  textarea: { width: "100%", boxSizing: "border-box", padding: "0.5rem", border: "1px solid #d1d5db", borderRadius: 6, fontSize: "0.9rem", marginBottom: "0.5rem" },
  btnSecondary: { padding: "0.45rem 1rem", background: "#f3f4f6", border: "1px solid #d1d5db", borderRadius: 6, cursor: "pointer", fontWeight: 500 },
  btnApprove: { padding: "0.55rem 1.25rem", background: "#16a34a", color: "#fff", border: "none", borderRadius: 6, fontSize: "0.95rem", cursor: "pointer", fontWeight: 600 },
  btnReject: { padding: "0.55rem 1.25rem", background: "#dc2626", color: "#fff", border: "none", borderRadius: 6, fontSize: "0.95rem", cursor: "pointer", fontWeight: 600 },
};
