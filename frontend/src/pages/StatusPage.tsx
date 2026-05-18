import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getEventStatus } from "@/api/events";
import type { EventStatus } from "@/types";

const STEPS: { key: EventStatus | "uploaded"; label: string }[] = [
  { key: "pending_upload", label: "Waiting for upload" },
  { key: "uploaded",       label: "Media uploaded" },
  { key: "transcribing",   label: "Transcribing audio" },
  { key: "drafting",       label: "Generating draft" },
  { key: "draft_ready",    label: "Draft ready for review" },
  { key: "approved",       label: "Approved" },
  { key: "rejected",       label: "Rejected" },
];

const STEP_KEYS = STEPS.map((s) => s.key);

const TERMINAL: EventStatus[] = ["approved", "rejected", "failed"];

export default function StatusPage() {
  const { eventId } = useParams<{ eventId: string }>();
  const navigate = useNavigate();

  const { data, isLoading } = useQuery({
    queryKey: ["event-status", eventId],
    queryFn: () => getEventStatus(eventId!),
    enabled: !!eventId,
    refetchInterval: (query) =>
      TERMINAL.includes(query.state.data?.status as EventStatus) ? false : 5000,
  });

  if (isLoading) return <div style={s.page}>Loading…</div>;
  if (!data) return <div style={s.page}>Event not found.</div>;

  const currentIdx = STEP_KEYS.indexOf(data.status as EventStatus);

  return (
    <div style={s.page}>
      <button style={s.back} onClick={() => navigate("/producer")}>← Back</button>
      <h1 style={s.heading}>{data.title}</h1>
      <p style={s.sub}>Auto-refreshes every 5 seconds until complete.</p>

      <div style={s.card}>
        {STEPS.map((step, i) => {
          const done = i < currentIdx;
          const active = i === currentIdx;
          return (
            <div key={step.key} style={s.step}>
              <div style={{ position: "relative", display: "flex", flexDirection: "column", alignItems: "center" }}>
                <div style={dot(done, active)} />
                {i < STEPS.length - 1 && <div style={line(done)} />}
              </div>
              <span style={{ color: i > currentIdx ? "#9ca3af" : "#111827", fontWeight: active ? 700 : 400, paddingTop: 1 }}>
                {step.label}
              </span>
            </div>
          );
        })}
      </div>

      <div style={s.card}>
        <Row label="Status"       value={data.status.replace(/_/g, " ")} />
        <Row label="Transcription" value={data.transcript_status ?? "—"} />
        <Row label="Draft"         value={data.draft_status ?? "—"} />
        <Row label="Review"        value={data.review_decision ?? "pending"} />
        <Row label="Created"       value={new Date(data.created_at).toLocaleString()} />
      </div>

      {(data.status === "draft_ready" || data.status === "approved" || data.status === "rejected") && (
        <button style={s.btn} onClick={() => navigate(`/review/${eventId}`)}>
          View Draft & Review →
        </button>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "0.45rem 0", borderBottom: "1px solid #f3f4f6" }}>
      <span style={{ color: "#6b7280", fontSize: "0.875rem" }}>{label}</span>
      <span style={{ fontWeight: 600, fontSize: "0.875rem" }}>{value}</span>
    </div>
  );
}

const dot = (done: boolean, active: boolean): React.CSSProperties => ({
  width: 16, height: 16, borderRadius: "50%", flexShrink: 0,
  background: done ? "#10b981" : active ? "#1d4ed8" : "#e5e7eb",
  border: active ? "2px solid #1d4ed8" : "none",
  zIndex: 1,
});

const line = (done: boolean): React.CSSProperties => ({
  width: 2, height: 24, background: done ? "#10b981" : "#e5e7eb",
});

const s: Record<string, React.CSSProperties> = {
  page: { maxWidth: 560, margin: "0 auto", padding: "2rem 1rem", fontFamily: "system-ui, sans-serif" },
  back: { background: "none", border: "none", cursor: "pointer", color: "#1d4ed8", padding: 0, marginBottom: "1rem", fontSize: "0.9rem" },
  heading: { fontSize: "1.5rem", fontWeight: 700, margin: 0 },
  sub: { color: "#6b7280", marginTop: 4, marginBottom: "1.5rem" },
  card: { background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, padding: "1.25rem", marginBottom: "1rem" },
  step: { display: "flex", gap: 14, marginBottom: "0.5rem" },
  btn: { padding: "0.55rem 1.25rem", background: "#1d4ed8", color: "#fff", border: "none", borderRadius: 6, fontSize: "0.95rem", cursor: "pointer", fontWeight: 600 },
};
