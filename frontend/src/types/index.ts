export type EventStatus =
  | "pending_upload"
  | "uploaded"
  | "transcribing"
  | "drafting"
  | "draft_ready"
  | "approved"
  | "rejected"
  | "failed";

export interface Event {
  id: string;
  title: string;
  description: string | null;
  producer_id: string;
  status: EventStatus;
  media_gcs_key: string | null;
  presigned_upload_url?: string;
  created_at: string;
  updated_at: string;
}

export interface EventStatusResponse {
  id: string;
  title: string;
  status: EventStatus;
  transcript_status: string | null;
  draft_status: string | null;
  review_decision: string | null;
  created_at: string;
  updated_at: string;
}

export interface Draft {
  id: string;
  event_id: string;
  content: string;
  llm_provider: string;
  llm_model: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  status: string;
  generated_at: string | null;
  created_at: string;
}

export interface Comment {
  id: string;
  review_id: string;
  author_id: string;
  author_role: "reviewer" | "producer";
  body: string;
  created_at: string;
}

export interface Review {
  id: string;
  draft_id: string;
  reviewer_id: string | null;
  decision: "approved" | "rejected" | null;
  decided_at: string | null;
  comments: Comment[];
  created_at: string;
  updated_at: string;
}
