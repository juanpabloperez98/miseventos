import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { forkJoin, map, type Observable, of, switchMap } from 'rxjs';

import { AuthService } from '../../../core/auth/auth.service';
import { API_URL } from '../../../core/config/api-url.token';
import { RequestCache } from '../../../shared/utils/request-cache';
import { type Speaker, type SpeakerPage } from '../models/speaker.model';

/** Largest page accepted by the backend. */
const PAGE_SIZE = 100;
/** How long the speaker catalog is reused before it is requested again. */
export const SPEAKERS_CACHE_TTL_MS = 60_000;

/** Read-only speaker catalog (`GET /speakers`), used to show and assign session speakers. */
@Injectable({ providedIn: 'root' })
export class SpeakersService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = inject(API_URL);
  private readonly auth = inject(AuthService);
  private readonly cache = new RequestCache<Speaker[]>(SPEAKERS_CACHE_TTL_MS);

  /**
   * Every speaker, ordered by name. Requests further pages only if there are more than 100.
   * Reused for 60 seconds within the same session (the key is the token sent with the request).
   */
  listAll(): Observable<Speaker[]> {
    return this.cache.get(this.auth.accessToken() ?? 'anonymous', () => this.loadAll());
  }

  private loadAll(): Observable<Speaker[]> {
    return this.page(1).pipe(
      switchMap((first) =>
        first.pages <= 1
          ? of(first.items)
          : forkJoin(
              Array.from({ length: first.pages - 1 }, (_, index) => this.page(index + 2)),
            ).pipe(map((rest) => [first, ...rest].flatMap((page) => page.items))),
      ),
    );
  }

  private page(page: number): Observable<SpeakerPage> {
    const params = new HttpParams().set('page', page).set('per_page', PAGE_SIZE);
    return this.http.get<SpeakerPage>(`${this.apiUrl}/speakers`, { params });
  }
}
