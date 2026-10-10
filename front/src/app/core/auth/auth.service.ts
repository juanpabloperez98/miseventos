import { HttpClient } from '@angular/common/http';
import { computed, DestroyRef, inject, Injectable, signal } from '@angular/core';
import {
  catchError,
  map,
  type Observable,
  of,
  Subject,
  switchMap,
  tap,
  throwError,
  timeout,
} from 'rxjs';

import { API_URL } from '../config/api-url.token';
import { toApiError } from '../http/api-error';
import { FlashMessageService } from '../services/flash-message.service';
import {
  type AccessToken,
  type LoginRequest,
  type RegisterRequest,
  type User,
} from './auth.models';
import { TokenStorage } from './token-storage';

const MAX_TIMER_DELAY = 2_147_483_647;
const RESTORE_TIMEOUT_MS = 8_000;

export type SessionEndReason = 'logout' | 'expired' | 'rejected';

/**
 * Single source of truth for the authentication state.
 *
 * The current user (and therefore its role) always comes from `GET /auth/me`, never from decoding
 * the JWT: the backend reads the role from the database on every request, and the UI mirrors it.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = inject(API_URL);
  private readonly storage = inject(TokenStorage);
  private readonly flashMessages = inject(FlashMessageService);

  private readonly currentUser = signal<User | null>(null);
  private readonly sessionEndedSubject = new Subject<SessionEndReason>();
  private expiryTimer: ReturnType<typeof setTimeout> | undefined;

  readonly user = this.currentUser.asReadonly();
  readonly isAuthenticated = computed(() => this.currentUser() !== null);
  readonly sessionEnded$ = this.sessionEndedSubject.asObservable();

  constructor() {
    inject(DestroyRef).onDestroy(() => clearTimeout(this.expiryTimer));
  }

  accessToken(): string | null {
    const stored = this.storage.read();
    if (!stored && this.currentUser()) {
      this.endSession('expired');
    }
    return stored?.value ?? null;
  }

  restoreSession(): Observable<void> {
    const stored = this.storage.read();
    if (!stored) {
      return of(undefined);
    }
    return this.fetchCurrentUser().pipe(
      timeout(RESTORE_TIMEOUT_MS),
      tap(() => this.scheduleExpiry(stored.expiresAt)),
      map(() => undefined),
      catchError((error: unknown) => {
        if (toApiError(error).status === 401) {
          this.endSession('rejected');
        }
        return of(undefined);
      }),
    );
  }

  login(credentials: LoginRequest): Observable<User> {
    return this.http.post<AccessToken>(`${this.apiUrl}/auth/login`, credentials).pipe(
      tap((token) => this.storage.save(token)),
      switchMap(() => this.fetchCurrentUser()),
      tap(() => {
        const stored = this.storage.read();
        if (stored) {
          this.scheduleExpiry(stored.expiresAt);
        }
      }),
      catchError((error: unknown) => {
        this.endSession('rejected');
        return throwError(() => error);
      }),
    );
  }

  register(data: RegisterRequest): Observable<User> {
    return this.http.post<User>(`${this.apiUrl}/auth/register`, data);
  }

  logout(): void {
    this.endSession('logout');
  }

  handleRejectedToken(): void {
    this.endSession('rejected');
  }

  private fetchCurrentUser(): Observable<User> {
    return this.http
      .get<User>(`${this.apiUrl}/auth/me`)
      .pipe(tap((user) => this.currentUser.set(user)));
  }

  private scheduleExpiry(expiresAt: number): void {
    clearTimeout(this.expiryTimer);
    const delay = Math.min(Math.max(expiresAt - Date.now(), 0), MAX_TIMER_DELAY);
    this.expiryTimer = setTimeout(() => this.endSession('expired'), delay);
  }

  /**
   * Clears the token, the user and any pending flash message (it may belong to the previous user).
   * Idempotent: concurrent 401 responses end the session, and notify listeners, only once.
   */
  private endSession(reason: SessionEndReason): void {
    clearTimeout(this.expiryTimer);
    this.storage.clear();
    if (this.currentUser() === null) {
      return;
    }
    this.currentUser.set(null);
    this.flashMessages.consume();
    this.sessionEndedSubject.next(reason);
  }
}
