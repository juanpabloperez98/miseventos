export interface EventSession {
  id: number;
  event_id: number;
  speaker_id: number | null;
  speaker_name: string | null;
  title: string;
  description: string | null;
  start_time: string;
  end_time: string;
  capacity: number;
  created_at?: string;
  updated_at?: string;
}

export interface SessionPayload {
  title: string;
  description: string | null;
  start_time: string;
  end_time: string;
  capacity: number;
  speaker_id: number | null;
}

export const SESSION_LIMITS = {
  titleMaxLength: 200,
  descriptionMaxLength: 5000,
  capacityMax: 1_000_000,
} as const;
