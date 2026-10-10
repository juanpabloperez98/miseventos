import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  type ElementRef,
  inject,
  input,
  signal,
  viewChild,
} from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { switchMap } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import { AuthorizationService } from '../../../../core/auth/authorization.service';
import { describeApiError } from '../../../../core/http/api-error';
import { FlashMessageService } from '../../../../core/services/flash-message.service';
import { Alert } from '../../../../shared/components/alert/alert';
import { Button } from '../../../../shared/components/button/button';
import { EmptyState } from '../../../../shared/components/empty-state/empty-state';
import { ErrorState } from '../../../../shared/components/error-state/error-state';
import { Loading } from '../../../../shared/components/loading/loading';
import { Pagination } from '../../../../shared/components/pagination/pagination';
import { LOADING, toRequestState } from '../../../../shared/utils/request-state';
import { EventCard } from '../../components/event-card/event-card';
import { EVENT_LIMITS } from '../../models/event.model';
import { EventsService } from '../../services/events.service';

export const EVENTS_PER_PAGE = 9;

function toPage(value: unknown): number {
  const page = Number(value);
  return Number.isInteger(page) && page > 0 ? page : 1;
}

function toSearch(value: unknown): string {
  return typeof value === 'string' ? value.trim().slice(0, EVENT_LIMITS.searchMaxLength) : '';
}

@Component({
  selector: 'app-event-list-page',
  imports: [
    ReactiveFormsModule,
    RouterLink,
    Alert,
    Button,
    EmptyState,
    ErrorState,
    EventCard,
    Loading,
    Pagination,
  ],
  templateUrl: './event-list-page.html',
  styleUrl: './event-list-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EventListPage {
  readonly page = input(1, { transform: toPage });
  readonly search = input('', { transform: toSearch });

  private readonly router = inject(Router);
  private readonly events = inject(EventsService);
  private readonly auth = inject(AuthService);
  protected readonly authorization = inject(AuthorizationService);

  protected readonly flash = inject(FlashMessageService).consume();
  protected readonly searchMaxLength = EVENT_LIMITS.searchMaxLength;
  protected readonly searchForm = inject(NonNullableFormBuilder).group({
    search: ['', [Validators.maxLength(EVENT_LIMITS.searchMaxLength)]],
  });
  private readonly searchControl = this.searchForm.controls.search;

  private readonly resultsHeading = viewChild<ElementRef<HTMLElement>>('resultsHeading');
  private readonly reloads = signal(0);

  private readonly query = computed(() => ({
    page: this.page(),
    search: this.search(),
    userId: this.auth.user()?.id ?? null,
    reload: this.reloads(),
  }));

  protected readonly state = toSignal(
    toObservable(this.query).pipe(
      switchMap(({ page, search }) =>
        this.events.list({ page, perPage: EVENTS_PER_PAGE, search }).pipe(toRequestState()),
      ),
    ),
    { initialValue: LOADING },
  );

  protected readonly errorMessage = computed(() => {
    const state = this.state();
    return state.status === 'error' ? describeApiError(state.error) : '';
  });

  constructor() {
    effect(() => this.searchControl.setValue(this.search(), { emitEvent: false }));
  }

  protected submitSearch(): void {
    if (this.searchControl.invalid) {
      return;
    }
    const search = this.searchControl.value.trim();
    this.navigate({ search: search || null, page: null });
  }

  protected clearSearch(): void {
    this.searchControl.setValue('');
    this.navigate({ search: null, page: null });
  }

  protected changePage(page: number): void {
    this.navigate({ page: page > 1 ? page : null }).then(() =>
      this.resultsHeading()?.nativeElement.focus({ preventScroll: false }),
    );
  }

  protected retry(): void {
    this.reloads.update((value) => value + 1);
  }

  private navigate(queryParams: Record<string, string | number | null>): Promise<boolean> {
    return this.router.navigate([], { queryParams, queryParamsHandling: 'merge' });
  }
}
