/** `SpeakerSchema` returned by `GET /speakers` (public data only, no email). */
export interface Speaker {
  id: number;
  name: string;
  bio: string | null;
}

/** `SpeakerPageSchema`. */
export interface SpeakerPage {
  items: Speaker[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}
