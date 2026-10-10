export type UserRole = 'ADMIN' | 'ORGANIZER' | 'ATTENDEE';

export interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  created_at?: string;
  updated_at?: string;
}

export interface AccessToken {
  access_token: string;
  token_type: string;
  expires_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  name: string;
  email: string;
  password: string;
}

export const ROLE_LABELS: Record<UserRole, string> = {
  ADMIN: 'Administrador',
  ORGANIZER: 'Organizador',
  ATTENDEE: 'Asistente',
};
