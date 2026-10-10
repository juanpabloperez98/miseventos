import { catchError, map, of, type OperatorFunction, startWith } from 'rxjs';

import { type ApiError, toApiError } from '../../core/http/api-error';

export type RequestState<T> =
  { status: 'loading' } | { status: 'success'; data: T } | { status: 'error'; error: ApiError };

export const LOADING: RequestState<never> = { status: 'loading' };

export function toRequestState<T>(): OperatorFunction<T, RequestState<T>> {
  return (source) =>
    source.pipe(
      map((data): RequestState<T> => ({ status: 'success', data })),
      startWith(LOADING),
      catchError((error: unknown) =>
        of<RequestState<T>>({ status: 'error', error: toApiError(error) }),
      ),
    );
}
