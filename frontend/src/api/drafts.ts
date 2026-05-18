import client from "./client";
import type { Draft, Review, Comment } from "@/types";

export const getDraftByEvent = async (eventId: string): Promise<Draft> => {
  const { data } = await client.get<Draft>(`/drafts/by-event/${eventId}`);
  return data;
};

export const getReview = async (draftId: string): Promise<Review> => {
  const { data } = await client.get<Review>(`/reviews/by-draft/${draftId}`);
  return data;
};

export const addComment = async (
  draftId: string,
  payload: { author_id: string; author_role: "reviewer" | "producer"; body: string }
): Promise<Comment> => {
  const { data } = await client.post<Comment>(`/reviews/by-draft/${draftId}/comments`, payload);
  return data;
};

export const submitDecision = async (
  draftId: string,
  payload: { reviewer_id: string; decision: "approved" | "rejected" }
): Promise<Review> => {
  const { data } = await client.post<Review>(`/reviews/by-draft/${draftId}/decision`, payload);
  return data;
};
