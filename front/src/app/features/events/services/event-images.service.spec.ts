import { HttpTestingController, type TestRequest } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import {
  buildImage,
  buildPage,
  cleanUpAuth,
  imageFile,
  provideTestDependencies,
  signInAs,
  TEST_API_URL,
  TEST_USERS,
} from '../../../../testing/test-helpers';
import {
  describeImageProgress,
  EventImageError,
  type EventImageProgress,
  EventImagesService,
  NO_IMAGE_CHANGE,
  type SignedImageUpload,
  validateEventImage,
} from './event-images.service';
import { EventsService } from './events.service';

const SIGNED: SignedImageUpload = {
  upload_url: 'https://api.cloudinary.com/v1_1/demo/image/upload',
  cloud_name: 'demo',
  api_key: '123456',
  timestamp: 1_900_000_000,
  signature: 'abc123',
  public_id: 'mis-eventos/events/10/0123456789abcdef0123456789abcdef',
  allowed_formats: 'jpg,png,webp',
};
const IMAGES_URL = `${TEST_API_URL}/events/10/images`;

describe('EventImagesService', () => {
  let service: EventImagesService;
  let http: HttpTestingController;
  let progress: EventImageProgress[];
  let failure: unknown;
  let completed: boolean;

  function run(observable: ReturnType<EventImagesService['upload']>): void {
    observable.subscribe({
      next: (value) => progress.push(value),
      error: (error: unknown) => (failure = error),
      complete: () => (completed = true),
    });
  }

  const authorization = () => http.expectOne(`${IMAGES_URL}/upload`);
  const cloudinary = () => http.expectOne(SIGNED.upload_url);
  const confirmation = () => http.expectOne(`${IMAGES_URL}/confirm`);
  const stages = () => progress.map((value) => value.stage);

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: provideTestDependencies() });
    service = TestBed.inject(EventImagesService);
    http = TestBed.inject(HttpTestingController);
    progress = [];
    failure = undefined;
    completed = false;
    signInAs(TEST_USERS.organizer);
  });

  afterEach(() => cleanUpAuth());

  describe('upload', () => {
    it('should ask the backend for a signature sending only the file metadata', () => {
      run(service.upload(10, imageFile('portada.png', 'image/png', 2048)));

      const request = authorization();
      expect(request.request.method).toBe('POST');
      expect(request.request.body).toEqual({
        filename: 'portada.png',
        content_type: 'image/png',
        size: 2048,
      });
      expect(request.request.headers.get('Authorization')).toBe('Bearer token-2');
      expect(stages()).toEqual(['authorizing']);
      request.flush(SIGNED);
      cloudinary().flush({});
      confirmation().flush(buildImage());
    });

    it('should send the file directly to Cloudinary with the signed parameters', () => {
      const file = imageFile();
      run(service.upload(10, file));
      authorization().flush(SIGNED);

      const request: TestRequest = cloudinary();
      expect(request.request.method).toBe('POST');
      const body = request.request.body as FormData;
      expect(body.get('file')).toBe(file);
      expect(body.get('api_key')).toBe('123456');
      expect(body.get('timestamp')).toBe('1900000000');
      expect(body.get('signature')).toBe('abc123');
      expect(body.get('public_id')).toBe(SIGNED.public_id);
      expect(body.get('allowed_formats')).toBe('jpg,png,webp');
      expect(body.has('api_secret')).toBeFalse();
      // The JWT of the API never reaches Cloudinary.
      expect(request.request.headers.has('Authorization')).toBeFalse();
      request.flush({ public_id: SIGNED.public_id });
      confirmation().flush(buildImage());
    });

    it('should confirm the upload and emit the saved image', () => {
      const image = buildImage();
      run(service.upload(10, imageFile()));
      authorization().flush(SIGNED);
      cloudinary().flush({});

      const request = confirmation();
      expect(request.request.body).toEqual({ public_id: SIGNED.public_id });
      request.flush(image);

      expect(stages()).toEqual(['authorizing', 'uploading', 'confirming', 'done']);
      expect(progress.at(-1)).toEqual({ stage: 'done', image });
      expect(completed).toBeTrue();
    });

    it('should forget the cached catalog once the image is saved', () => {
      const events = TestBed.inject(EventsService);
      events.list({ page: 1, perPage: 9 }).subscribe();
      http.expectOne((req) => req.url === `${TEST_API_URL}/events`).flush(buildPage([]));

      run(service.upload(10, imageFile()));
      authorization().flush(SIGNED);
      cloudinary().flush({});
      confirmation().flush(buildImage());

      events.list({ page: 1, perPage: 9 }).subscribe();
      http.expectOne((req) => req.url === `${TEST_API_URL}/events`).flush(buildPage([]));
    });

    it('should validate the file before sending any request', () => {
      run(service.upload(10, imageFile('doc.pdf', 'application/pdf')));

      http.expectNone(`${IMAGES_URL}/upload`);
      expect(failure).toEqual(
        new EventImageError('validation', 'Selecciona una imagen JPG, PNG o WebP.'),
      );
    });

    it('should report a rejected authorization and stop', () => {
      run(service.upload(10, imageFile()));
      authorization().flush(
        { message: 'You can only manage your own events' },
        { status: 403, statusText: 'Forbidden' },
      );

      http.expectNone(SIGNED.upload_url);
      expect((failure as EventImageError).stage).toBe('authorization');
      expect((failure as EventImageError).message).toBe(
        'No tienes permiso para realizar esta acción.',
      );
    });

    it('should explain when uploads are not configured', () => {
      run(service.upload(10, imageFile()));
      authorization().flush(
        { message: 'Image uploads are not configured' },
        { status: 503, statusText: 'Service Unavailable' },
      );

      expect((failure as EventImageError).message).toBe(
        'La carga de imágenes no está disponible en este momento.',
      );
    });

    it('should report a failed upload to Cloudinary without confirming', () => {
      run(service.upload(10, imageFile()));
      authorization().flush(SIGNED);
      cloudinary().flush(
        { error: { message: 'Invalid signature' } },
        { status: 401, statusText: 'Unauthorized' },
      );

      http.expectNone(`${IMAGES_URL}/confirm`);
      expect((failure as EventImageError).stage).toBe('upload');
    });

    it('should report a rejected confirmation', () => {
      run(service.upload(10, imageFile()));
      authorization().flush(SIGNED);
      cloudinary().flush({});
      confirmation().flush(
        { message: 'The uploaded image could not be verified' },
        { status: 422, statusText: 'Unprocessable Entity' },
      );

      expect((failure as EventImageError).stage).toBe('confirmation');
      expect((failure as EventImageError).message).toBe(
        'No se pudo verificar la imagen subida. Inténtalo de nuevo.',
      );
    });

    it('should cancel the upload in flight when unsubscribed', () => {
      const subscription = service.upload(10, imageFile()).subscribe();
      authorization().flush(SIGNED);
      const request = cloudinary();

      subscription.unsubscribe();

      expect(request.cancelled).toBeTrue();
      http.expectNone(`${IMAGES_URL}/confirm`);
    });
  });

  describe('remove and apply', () => {
    it('should remove the cover with DELETE', () => {
      run(service.remove(10));

      const request = http.expectOne(IMAGES_URL);
      expect(request.request.method).toBe('DELETE');
      request.flush(null, { status: 204, statusText: 'No Content' });
      expect(progress).toEqual([{ stage: 'removing' }, { stage: 'done', image: null }]);
    });

    it('should report a failed removal', () => {
      run(service.remove(10));
      http
        .expectOne(IMAGES_URL)
        .flush({ message: 'x' }, { status: 502, statusText: 'Bad Gateway' });

      expect((failure as EventImageError).stage).toBe('removal');
    });

    it('should do nothing when the image did not change', () => {
      run(service.apply(10, NO_IMAGE_CHANGE));

      expect(progress).toEqual([]);
      expect(completed).toBeTrue();
    });

    it('should upload a new file or remove the image as chosen', () => {
      run(service.apply(10, { file: null, remove: true }));
      http.expectOne(IMAGES_URL).flush(null, { status: 204, statusText: 'No Content' });

      run(service.apply(10, { file: imageFile(), remove: false }));
      authorization().flush(SIGNED);
      cloudinary().flush({});
      confirmation().flush(buildImage());
      expect(progress.at(-1)?.stage).toBe('done');
    });
  });

  describe('helpers', () => {
    it('should accept only JPEG, PNG and WebP up to 5 MB', () => {
      expect(validateEventImage(imageFile('a.jpg', 'image/jpeg'))).toBeNull();
      expect(validateEventImage(imageFile('a.png', 'image/png'))).toBeNull();
      expect(validateEventImage(imageFile('a.webp', 'image/webp'))).toBeNull();
      expect(validateEventImage(imageFile('a.gif', 'image/gif'))).toContain('JPG, PNG o WebP');
      expect(validateEventImage(imageFile('a.svg', 'image/svg+xml'))).toContain('JPG');
      expect(validateEventImage(imageFile('a.jpg', 'image/jpeg', 0))).toBe(
        'El archivo está vacío.',
      );
      expect(validateEventImage(imageFile('a.jpg', 'image/jpeg', 5 * 1024 * 1024))).toBeNull();
      expect(validateEventImage(imageFile('a.jpg', 'image/jpeg', 5 * 1024 * 1024 + 1))).toBe(
        'La imagen no puede superar 5 MB.',
      );
    });

    it('should describe each stage', () => {
      expect(describeImageProgress({ stage: 'uploading', percent: 40 })).toBe(
        'Subiendo la imagen… 40 %',
      );
      expect(describeImageProgress({ stage: 'uploading', percent: null })).toBe(
        'Subiendo la imagen…',
      );
      expect(describeImageProgress({ stage: 'confirming' })).toBe('Guardando la imagen…');
    });
  });
});
