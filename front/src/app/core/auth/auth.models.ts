/** Roles defined by the backend (`UserRole`). */
export type UserRole = 'ADMIN' | 'ORGANIZER' | 'ATTENDEE';

/** `UserSchema` returned by `POST /auth/register` and `GET /auth/me`. */
export interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  created_at?: string;
  updated_at?: string;
}

/** `AccessTokenSchema` returned by `POST /auth/login`. */
export interface AccessToken {
  access_token: string;
  token_type: string;
  /** ISO 8601 date with timezone. */
  expires_at: string;
}

/** Body of `POST /auth/login`. */
export interface LoginRequest {
  email: string;
  password: string;
}

/** Body of `POST /auth/register`. The backend always creates an `ATTENDEE`. */
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
