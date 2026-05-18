import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { createEvent, listEvents, uploadMedia } from "@/api/events";
import type { Event } from "@/types";

const PRODUCER_ID = "producer-demo";

const STATUS_COLOR: Record<string, string> = {
  pending_upload: "#f59e0b",
  uploaded: "#3b82f6",
  transcribing: "#8b5cf6",
  drafting: "#8b5cf6",
  draft_ready: "#10b981",
  approved: "#16a34a",
  rejected: "#ef4444",
  failed: "#dc2626",
};

export default function ProducerPage() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);

  const { data: events, refetch } = useQuery({
    queryKey: ["events", PRODUCER_ID],
    queryFn: () => listEvents(PRODUCER_ID),
  });

  const create = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Please select a media file");
      const event = await createEvent({ title, description, producer_id: PRODUCER_ID });
      setUploadMsg("Uploading media…");
      await uploadMedia(event.presigned_upload_url!, file);
      setUploadMsg("Upload complete!");
      return event;
    },
    onSuccess: (event) => {
      refetch();
      setTimeout(() => navigate(`/producer/${event.id}/status`), 800);
    },
    onError: (err: Error) => {
      setUploadMsg(null);
      alert(err.message);
    },
  });

  return (
    <div style={s.page}>
      <h1 style={s.heading}>Marketing Content Generation</h1>
      <p style={s.sub}>Create an event, upload your media, and let AI generate the draft.</p>

      <div style={s.card}>
        <h2 style={s.cardTitle}>New Event</h2>
        <label style={s.label}>Title *</label>
        <input
          style={s.input}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Product Launch Q2 2026"
        />
        <label style={s.label}>Description</label>
        <textarea
          style={{ ...s.input, minHeight: 72, resize: "vertical" }}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Brief context for the AI…"
        />
        <label style={s.label}>Media file (audio or video) *</label>
        <input
          type="file"
          accept="audio/*,video/*"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          style={{ marginBottom: 8 }}
        />
        {file && (
          <p style={s.hint}>{file.name} — {(file.size / 1024 / 1024).toFixed(1)} MB</p>
        )}
        {uploadMsg && <p style={s.progress}>{uploadMsg}</p>}
        <button
          style={s.btn}
          disabled={!title || !file || create.isPending}
          onClick={() => create.mutate()}
        >
          {create.isPending ? "Creating…" : "Create & Upload"}
        </button>
      </div>

      {events && events.length > 0 && (
        <div style={s.card}>
          <h2 style={s.cardTitle}>My Events</h2>
          {events.map((ev) => (
            <EventRow key={ev.id} event={ev} onClick={() => navigate(`/producer/${ev.id}/status`)} />
          ))}
        </div>
      )}
    </div>
  );
}

function EventRow({ event, onClick }: { event: Event; onClick: () => void }) {
  const label = event.status.replace(/_/g, " ");
  const color = STATUS_COLOR[event.status] ?? "#6b7280";
  return (
    <div style={s.row} onClick={onClick}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <strong>{event.title}</strong>
        <span style={{ ...s.badge, background: color }}>{label}</span>
      </div>
      <span style={s.date}>{new Date(event.created_at).toLocaleDateString()}</span>
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  page: { maxWidth: 680, margin: "0 auto", padding: "2rem 1rem", fontFamily: "system-ui, sans-serif" },
  heading: { fontSize: "1.75rem", fontWeight: 700, margin: 0 },
  sub: { color: "#6b7280", marginTop: 4, marginBottom: "2rem" },
  card: { background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, padding: "1.5rem", marginBottom: "1.25rem" },
  cardTitle: { fontSize: "1.05rem", fontWeight: 600, marginTop: 0, marginBottom: "1rem" },
  label: { display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: 4 },
  input: { width: "100%", boxSizing: "border-box", padding: "0.5rem 0.75rem", border: "1px solid #d1d5db", borderRadius: 6, fontSize: "0.95rem", marginBottom: "1rem" },
  hint: { fontSize: "0.8rem", color: "#6b7280", margin: "0 0 0.75rem" },
  progress: { color: "#3b82f6", fontWeight: 500, marginBottom: "0.75rem" },
  btn: { padding: "0.55rem 1.25rem", background: "#1d4ed8", color: "#fff", border: "none", borderRadius: 6, fontSize: "0.95rem", cursor: "pointer", fontWeight: 600 },
  row: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.65rem 0", borderBottom: "1px solid #f3f4f6", cursor: "pointer" },
  badge: { padding: "2px 8px", borderRadius: 12, fontSize: "0.7rem", fontWeight: 700, color: "#fff" },
  date: { fontSize: "0.78rem", color: "#9ca3af" },
};
