export interface Speaker {
  id: number;
  name: string;
  bio: string | null;
}

export interface SpeakerPage {
  items: Speaker[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}
