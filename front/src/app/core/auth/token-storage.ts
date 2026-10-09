import { Injectable } from '@angular/core';

import { type AccessToken } from './auth.models';

const STORAGE_KEY = 'mis-eventos.access-token';

interface StoredToken {
  value: string;
  /** Expiry as epoch milliseconds. */
  expiresAt: number;
}

/**
 * Persists the access token in `sessionStorage`.
 *
 * The backend only accepts `Authorization: Bearer` headers (no cookies), so the token must be
 * readable by JavaScript. `sessionStorage` keeps the session across reloads of the same tab and is
 * discarded when the tab closes, which limits the exposure window compared with `localStorage`.
 * Like any script-readable storage it is exposed to XSS, so the app never renders untrusted HTML.
 */
@Injectable({ providedIn: 'root' })
export class TokenStorage {
  /** Fallback when `sessionStorage` is unavailable (the session then lasts until reload). */
  private memory: StoredToken | null = null;

  /** Returns the stored token, or `null` when there is none or it has expired. */
  read(): StoredToken | null {
    const stored = this.load();
    if (!stored) {
      return null;
    }
    if (stored.expiresAt <= Date.now()) {
      this.clear();
      return null;
    }
    return stored;
  }

  save(token: AccessToken): void {
    const expiresAt = Date.parse(token.expires_at);
    const stored: StoredToken = {
      value: token.access_token,
      // An unparseable expiry is treated as already expired rather than as "never expires".
      expiresAt: Number.isFinite(expiresAt) ? expiresAt : 0,
    };
    this.memory = stored;
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
    } catch {
      // Storage unavailable: keep the in-memory copy only.
    }
  }

  clear(): void {
    this.memory = null;
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      // Nothing to clear.
    }
  }

  private load(): StoredToken | null {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (raw === null) {
        return this.memory;
      }
      const parsed: unknown = JSON.parse(raw);
      return isStoredToken(parsed) ? parsed : null;
    } catch {
      return this.memory;
    }
  }
}

function isStoredToken(value: unknown): value is StoredToken {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const candidate = value as Partial<StoredToken>;
  return typeof candidate.value === 'string' && typeof candidate.expiresAt === 'number';
}
