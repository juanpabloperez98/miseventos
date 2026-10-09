import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { forkJoin, map, type Observable, of, switchMap } from 'rxjs';

import { API_URL } from '../../../core/config/api-url.token';
import { type Speaker, type SpeakerPage } from '../models/speaker.model';

/** Largest page accepted by the backend. */
const PAGE_SIZE = 100;

/** Read-only speaker catalog (`GET /speakers`), used to show and assign session speakers. */
@Injectable({ providedIn: 'root' })
export class SpeakersService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = inject(API_URL);

  /** Every speaker, ordered by name. Requests further pages only if there are more than 100. */
  listAll(): Observable<Speaker[]> {
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
