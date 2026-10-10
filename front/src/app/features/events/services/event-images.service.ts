import { HttpClient, HttpEventType } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import {
  catchError,
  concat,
  defer,
  filter,
  map,
  type Observable,
  of,
  startWith,
  switchMap,
  tap,
  throwError,
} from 'rxjs';

import { API_URL } from '../../../core/config/api-url.token';
import { describeApiError, toApiError } from '../../../core/http/api-error';
import { type EventImage } from '../models/event.model';
import { EventsService } from './events.service';

export const EVENT_IMAGE_RULES = {
  maxBytes: 5 * 1024 * 1024,
  types: ['image/jpeg', 'image/png', 'image/webp'],
} as const;

export interface SignedImageUpload {
  upload_url: string;
  cloud_name: string;
  api_key: string;
  timestamp: number;
  signature: string;
  public_id: string;
  allowed_formats: string;
}

export interface EventImageSelection {
  file: File | null;
  remove: boolean;
}

export const NO_IMAGE_CHANGE: EventImageSelection = { file: null, remove: false };

export type EventImageProgress =
  | { stage: 'authorizing' }
  | { stage: 'uploading'; percent: number | null }
  | { stage: 'confirming' }
  | { stage: 'removing' }
  | { stage: 'done'; image: EventImage | null };

export type EventImageStage =
  'validation' | 'authorization' | 'upload' | 'confirmation' | 'removal';

export class EventImageError extends Error {
  constructor(
    readonly stage: EventImageStage,
    message: string,
  ) {
    super(message);
    this.name = 'EventImageError';
  }
}

export function validateEventImage(file: File): string | null {
  if (!(EVENT_IMAGE_RULES.types as readonly string[]).includes(file.type)) {
    return 'Selecciona una imagen JPG, PNG o WebP.';
  }
  if (file.size === 0) {
    return 'El archivo está vacío.';
  }
  if (file.size > EVENT_IMAGE_RULES.maxBytes) {
    return `La imagen no puede superar ${EVENT_IMAGE_RULES.maxBytes / (1024 * 1024)} MB.`;
  }
  return null;
}

export function describeImageProgress(progress: EventImageProgress): string {
  switch (progress.stage) {
    case 'authorizing':
      return 'Preparando la subida de la imagen…';
    case 'uploading':
      return progress.percent === null
        ? 'Subiendo la imagen…'
        : `Subiendo la imagen… ${progress.percent} %`;
    case 'confirming':
      return 'Guardando la imagen…';
    case 'removing':
      return 'Quitando la imagen…';
    case 'done':
      return 'Imagen guardada.';
  }
}

/**
 * Cover image of an event:
 * 1. `POST /events/{id}/images/upload` with the file metadata → signed upload parameters.
 * 2. The file goes directly from the browser to Cloudinary (never through the backend). The auth
 *    interceptor only adds the JWT to API requests, so it never reaches Cloudinary.
 * 3. `POST /events/{id}/images/confirm` with the `public_id`; the backend verifies it with
 *    Cloudinary and saves it.
 *
 * Unsubscribing cancels the request in flight. Each stage reports its own error.
 */
@Injectable({ providedIn: 'root' })
export class EventImagesService {
  private readonly http = inject(HttpClient);
  private readonly events = inject(EventsService);
  private readonly baseUrl = `${inject(API_URL)}/events`;

  apply(eventId: number, selection: EventImageSelection): Observable<EventImageProgress> {
    if (selection.file) {
      return this.upload(eventId, selection.file);
    }
    return selection.remove ? this.remove(eventId) : of();
  }

  upload(eventId: number, file: File): Observable<EventImageProgress> {
    return defer(() => {
      const problem = validateEventImage(file);
      if (problem) {
        return throwError(() => new EventImageError('validation', problem));
      }
      const authorization = this.http
        .post<SignedImageUpload>(`${this.imagesUrl(eventId)}/upload`, {
          filename: file.name,
          content_type: file.type,
          size: file.size,
        })
        .pipe(catchError((error: unknown) => fail('authorization', apiMessage(error))));

      return authorization.pipe(
        switchMap((signed) =>
          concat(
            this.sendToCloudinary(signed, file),
            of<EventImageProgress>({ stage: 'confirming' }),
            this.confirm(eventId, signed.public_id),
          ),
        ),
        startWith<EventImageProgress>({ stage: 'authorizing' }),
      );
    });
  }

  remove(eventId: number): Observable<EventImageProgress> {
    return this.http.delete<void>(this.imagesUrl(eventId)).pipe(
      tap(() => this.events.clearListCache()),
      map((): EventImageProgress => ({ stage: 'done', image: null })),
      catchError((error: unknown) => fail('removal', apiMessage(error))),
      startWith<EventImageProgress>({ stage: 'removing' }),
    );
  }

  private sendToCloudinary(signed: SignedImageUpload, file: File): Observable<EventImageProgress> {
    const body = new FormData();
    body.append('file', file);
    body.append('api_key', signed.api_key);
    body.append('timestamp', String(signed.timestamp));
    body.append('signature', signed.signature);
    body.append('public_id', signed.public_id);
    body.append('allowed_formats', signed.allowed_formats);

    return this.http
      .post(signed.upload_url, body, { reportProgress: true, observe: 'events' })
      .pipe(
        // The fetch backend does not report upload progress: the status then has no percentage.
        filter((event) => event.type === HttpEventType.UploadProgress),
        map((event): EventImageProgress => ({
          stage: 'uploading',
          percent: event.total ? Math.round((100 * event.loaded) / event.total) : null,
        })),
        startWith<EventImageProgress>({ stage: 'uploading', percent: null }),
        catchError(() =>
          fail('upload', 'No se pudo subir la imagen a Cloudinary. Inténtalo de nuevo.'),
        ),
      );
  }

  private confirm(eventId: number, publicId: string): Observable<EventImageProgress> {
    return this.http
      .post<EventImage>(`${this.imagesUrl(eventId)}/confirm`, { public_id: publicId })
      .pipe(
        tap(() => this.events.clearListCache()),
        map((image): EventImageProgress => ({ stage: 'done', image })),
        catchError((error: unknown) => fail('confirmation', apiMessage(error))),
      );
  }

  private imagesUrl(eventId: number): string {
    return `${this.baseUrl}/${eventId}/images`;
  }
}

function fail(stage: EventImageStage, message: string): Observable<never> {
  return throwError(() => new EventImageError(stage, message));
}

function apiMessage(error: unknown): string {
  return describeApiError(toApiError(error));
}
