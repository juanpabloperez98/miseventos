import { type Observable, shareReplay, tap } from 'rxjs';

interface Entry<T> {
  response: Observable<T>;
  expiresAt: number;
}

/**
 * In-memory cache of GET responses, keyed by the caller.
 *
 * - Identical requests made while one is in flight share it (a single HTTP call).
 * - A successful response is reused for `ttlMs` after it arrives, then requested again.
 * - Errors are never kept: the entry is dropped and the next call retries.
 * - If every subscriber leaves before the response arrives, the request is cancelled and the next
 *   subscriber starts it again (`refCount`).
 *
 * The key must include whatever changes the response (query and session), so users never share
 * responses that depend on their permissions.
 */
export class RequestCache<T> {
  private readonly entries = new Map<string, Entry<T>>();

  constructor(
    private readonly ttlMs: number,
    private readonly now: () => number = () => Date.now(),
  ) {}

  get(key: string, load: () => Observable<T>): Observable<T> {
    this.dropExpired();
    const cached = this.entries.get(key);
    if (cached) {
      return cached.response;
    }

    const entry: Entry<T> = {
      response: undefined as unknown as Observable<T>,
      expiresAt: Infinity,
    };
    entry.response = load().pipe(
      tap({
        next: () => (entry.expiresAt = this.now() + this.ttlMs),
        error: () => this.remove(key, entry),
      }),
      shareReplay({ bufferSize: 1, refCount: true }),
    );
    this.entries.set(key, entry);
    return entry.response;
  }

  clear(): void {
    this.entries.clear();
  }

  private remove(key: string, entry: Entry<T>): void {
    // Only the failed entry: a newer one may already use the same key.
    if (this.entries.get(key) === entry) {
      this.entries.delete(key);
    }
  }

  private dropExpired(): void {
    const now = this.now();
    for (const [key, entry] of this.entries) {
      if (entry.expiresAt <= now) {
        this.entries.delete(key);
      }
    }
  }
}
