import { HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { type User } from '../../../../core/auth/auth.models';
import { FlashMessageService } from '../../../../core/services/flash-message.service';
import {
  BlankPage,
  buildEvent,
  buildImage,
  cleanUpAuth,
  imageFile,
  provideTestDependencies,
  selectFile,
  signInAs,
  TEST_API_URL,
  TEST_USERS,
  textOf,
} from '../../../../../testing/test-helpers';
import { type EventModel } from '../../models/event.model';
import { EventEditPage } from './event-edit-page';

describe('EventEditPage', () => {
  let harness: RouterTestingHarness;
  let http: HttpTestingController;

  const page = () => harness.routeNativeElement as HTMLElement;

  async function open(user: User, event: EventModel = buildEvent()): Promise<void> {
    signInAs(user);
    await harness.navigateByUrl(`/events/${event.id}/edit`, EventEditPage);
    TestBed.tick();
    http.expectOne(`${TEST_API_URL}/events/${event.id}`).flush(event);
    await harness.fixture.whenStable();
  }

  async function submit(): Promise<void> {
    page().querySelector<HTMLButtonElement>('button[type="submit"]')?.click();
    await harness.fixture.whenStable();
  }

  beforeEach(async () => {
    TestBed.configureTestingModule({
      providers: provideTestDependencies([
        { path: 'events/:id', component: BlankPage },
        { path: 'events/:id/edit', component: EventEditPage },
      ]),
    });
    harness = await RouterTestingHarness.create();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => cleanUpAuth());

  it('should not show the form to an organizer who does not own the event', async () => {
    await open(TEST_USERS.otherOrganizer);

    expect(page().querySelector('app-event-form')).toBeNull();
    expect(textOf(page().querySelector('app-error-state'))).toContain(
      'No puedes editar este evento',
    );
  });

  it('should not show the form for final events', async () => {
    await open(TEST_USERS.admin, buildEvent({ status: 'CANCELLED' }));
    expect(page().querySelector('app-event-form')).toBeNull();
  });

  it('should save with PUT and go back to the detail with a confirmation', async () => {
    await open(TEST_USERS.organizer);
    await submit();

    const request = http.expectOne(`${TEST_API_URL}/events/10`);
    expect(request.request.method).toBe('PUT');
    expect(request.request.body.name).toBe('Angular Summit');
    expect('status' in request.request.body).toBeFalse();
    request.flush(buildEvent());
    await harness.fixture.whenStable();

    expect(TestBed.inject(Router).url).toBe('/events/10');
    expect(TestBed.inject(FlashMessageService).consume()?.type).toBe('success');
  });

  it('should show conflicts returned by the backend and allow retrying', async () => {
    await open(TEST_USERS.organizer);
    await submit();

    http
      .expectOne(`${TEST_API_URL}/events/10`)
      .flush(
        { message: 'Capacity cannot be lower than the number of registered attendees' },
        { status: 409, statusText: 'Conflict' },
      );
    await harness.fixture.whenStable();

    expect(textOf(page().querySelector('app-alert'))).toBe(
      'La capacidad no puede ser menor que el número de personas inscritas.',
    );
    expect(page().querySelector<HTMLButtonElement>('button[type="submit"]')?.disabled).toBeFalse();
  });

  describe('cover image', () => {
    const IMAGES_URL = `${TEST_API_URL}/events/10/images`;
    const SIGNED = {
      upload_url: 'https://api.cloudinary.com/v1_1/demo/image/upload',
      cloud_name: 'demo',
      api_key: '123456',
      timestamp: 1_900_000_000,
      signature: 'abc123',
      public_id: 'mis-eventos/events/10/fedcba9876543210fedcba9876543210',
      allowed_formats: 'jpg,png,webp',
    };
    const fileInput = () => page().querySelector('input[type="file"]') as HTMLInputElement;
    const imageButton = () =>
      page().querySelector<HTMLButtonElement>('app-event-image-field button');

    async function saveEvent(): Promise<void> {
      await submit();
      http.expectOne({ method: 'PUT', url: `${TEST_API_URL}/events/10` }).flush(buildEvent());
      await harness.fixture.whenStable();
    }

    beforeEach(() => spyOn(URL, 'createObjectURL').and.returnValue('blob:preview'));

    it('should show the saved image and keep it when it is not changed', async () => {
      await open(TEST_USERS.organizer, buildEvent({ image: buildImage() }));
      expect(page().querySelector('app-event-image-field img')?.getAttribute('src')).toContain(
        'f_auto,q_auto',
      );

      await saveEvent();

      http.expectNone((request) => request.url.startsWith(IMAGES_URL));
      expect(TestBed.inject(Router).url).toBe('/events/10');
    });

    it('should replace the image after saving the event', async () => {
      await open(TEST_USERS.organizer, buildEvent({ image: buildImage() }));
      selectFile(fileInput(), imageFile('nueva.webp', 'image/webp'));
      await harness.fixture.whenStable();

      await saveEvent();
      const authorization = http.expectOne(`${IMAGES_URL}/upload`);
      expect(authorization.request.body.content_type).toBe('image/webp');
      authorization.flush(SIGNED);
      http.expectOne(SIGNED.upload_url).flush({});
      http.expectOne(`${IMAGES_URL}/confirm`).flush(buildImage({ public_id: SIGNED.public_id }));
      await harness.fixture.whenStable();

      expect(TestBed.inject(Router).url).toBe('/events/10');
      expect(TestBed.inject(FlashMessageService).consume()?.type).toBe('success');
    });

    it('should remove the image when asked to', async () => {
      await open(TEST_USERS.organizer, buildEvent({ image: buildImage() }));
      imageButton()?.click();
      await harness.fixture.whenStable();

      await saveEvent();
      const removal = http.expectOne(IMAGES_URL);
      expect(removal.request.method).toBe('DELETE');
      removal.flush(null, { status: 204, statusText: 'No Content' });
      await harness.fixture.whenStable();

      expect(TestBed.inject(Router).url).toBe('/events/10');
    });

    it('should stay on the page to retry when the image cannot be saved', async () => {
      await open(TEST_USERS.organizer);
      selectFile(fileInput(), imageFile());
      await harness.fixture.whenStable();

      await saveEvent();
      http
        .expectOne(`${IMAGES_URL}/upload`)
        .flush(
          { message: 'Image uploads are not configured' },
          { status: 503, statusText: 'Service Unavailable' },
        );
      await harness.fixture.whenStable();

      expect(TestBed.inject(Router).url).toBe('/events/10/edit');
      expect(textOf(page().querySelector('app-alert'))).toBe(
        'Los datos del evento se guardaron, pero la imagen no: La carga de imágenes no está disponible en este momento.',
      );
      expect(
        page().querySelector<HTMLButtonElement>('button[type="submit"]')?.disabled,
      ).toBeFalse();
    });
  });
});
