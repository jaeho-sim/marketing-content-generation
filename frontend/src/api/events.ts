import client from "./client";
import type { Event, EventStatusResponse } from "@/types";

export const createEvent = async (payload: {
  title: string;
  description?: string;
  producer_id: string;
}): Promise<Event> => {
  const { data } = await client.post<Event>("/events", payload);
  return data;
};

export const getEvent = async (id: string): Promise<Event> => {
  const { data } = await client.get<Event>(`/events/${id}`);
  return data;
};

export const listEvents = async (producer_id?: string): Promise<Event[]> => {
  const { data } = await client.get<Event[]>("/events", {
    params: producer_id ? { producer_id } : {},
  });
  return data;
};

export const getEventStatus = async (id: string): Promise<EventStatusResponse> => {
  const { data } = await client.get<EventStatusResponse>(`/events/${id}/status`);
  return data;
};

export const uploadMedia = async (presignedUrl: string, file: File): Promise<void> => {
  const res = await fetch(presignedUrl, {
    method: "PUT",
    body: file,
    headers: { "Content-Type": file.type },
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
};
