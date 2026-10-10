import { HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { FlashMessageService } from '../../../../core/services/flash-message.service';
import {
  BlankPage,
  buildEvent,
  buildImage,
  cleanUpAuth,
  fillDateTime,
  imageFile,
  provideTestDependencies,
  selectFile,
  signInAs,
  TEST_API_URL,
  TEST_USERS,
  textOf,
} from '../../../../../testing/test-helpers';
import { type SignedImageUpload } from '../../services/event-images.service';
import { EventCreatePage } from './event-create-page';

const SIGNED: SignedImageUpload = {
  upload_url: 'https://api.cloudinary.com/v1_1/demo/image/upload',
  cloud_name: 'demo',
  api_key: '123456',
  timestamp: 1_900_000_000,
  signature: 'abc123',
  public_id: 'mis-eventos/events/10/0123456789abcdef0123456789abcdef',
  allowed_formats: 'jpg,png,webp',
};

describe('EventCreatePage', () => {
  let harness: RouterTestingHarness;
  let http: HttpTestingController;

  const page = () => harness.routeNativeElement as HTMLElement;
  const submitButton = () => page().querySelector('button[type="submit"]') as HTMLButtonElement;

  function fill(label: string, value: string): void {
    const field = [...page().querySelectorAll('app-form-field')].find((candidate) =>
      textOf(candidate.querySelector('label')).startsWith(label),
    );
    if (!field) {
      throw new Error(`Field not found: ${label}`);
    }
    if (field.querySelector('app-date-time-input')) {
      fillDateTime(field, value);
      return;
    }
    const control = field.querySelector('input') as HTMLInputElement;
    control.value = value;
    control.dispatchEvent(new Event('input'));
  }

  async function fillAndSubmit(): Promise<void> {
    fill('Nombre', 'Angular Day');
    fill('Ubicación', 'Bogotá');
    fill('Inicio', '2030-05-10T10:00');
    fill('Finalización', '2030-05-10T18:00');
    fill('Capacidad', '100');
    await harness.fixture.whenStable();
    submitButton().click();
    await harness.fixture.whenStable();
  }

  beforeEach(async () => {
    TestBed.configureTestingModule({
      providers: provideTestDependencies([
        { path: 'events/new', component: EventCreatePage },
        { path: 'events/:id', component: BlankPage },
      ]),
    });
    harness = await RouterTestingHarness.create();
    http = TestBed.inject(HttpTestingController);
    signInAs(TEST_USERS.organizer);
    await harness.navigateByUrl('/events/new', EventCreatePage);
  });

  afterEach(() => cleanUpAuth());

  it('should create the event without image requests when no image is chosen', async () => {
    await fillAndSubmit();
    http.expectOne(`${TEST_API_URL}/events`).flush(buildEvent());
    await harness.fixture.whenStable();

    http.expectNone(`${TEST_API_URL}/events/10/images/upload`);
    expect(TestBed.inject(Router).url).toBe('/events/10');
    expect(TestBed.inject(FlashMessageService).consume()).toEqual({
      type: 'success',
      text: 'Evento creado como borrador.',
    });
  });

  it('should upload the chosen image after creating the event', async () => {
    spyOn(URL, 'createObjectURL').and.returnValue('blob:preview');
    selectFile(page().querySelector('input[type="file"]') as HTMLInputElement, imageFile());
    await fillAndSubmit();

    http.expectOne(`${TEST_API_URL}/events`).flush(buildEvent());
    await harness.fixture.whenStable();
    expect(submitButton().disabled).toBeTrue();
    expect(textOf(page().querySelector('[role="status"]'))).toBe(
      'Preparando la subida de la imagen…',
    );

    // A second click while uploading sends nothing.
    submitButton().click();
    http.expectOne(`${TEST_API_URL}/events/10/images/upload`).flush(SIGNED);
    http.expectOne(SIGNED.upload_url).flush({});
    http.expectOne(`${TEST_API_URL}/events/10/images/confirm`).flush(buildImage());
    await harness.fixture.whenStable();

    http.expectNone(`${TEST_API_URL}/events`);
    expect(TestBed.inject(Router).url).toBe('/events/10');
    expect(TestBed.inject(FlashMessageService).consume()?.text).toBe(
      'Evento creado como borrador, con su imagen.',
    );
  });

  it('should keep the event and explain the problem when the image fails', async () => {
    spyOn(URL, 'createObjectURL').and.returnValue('blob:preview');
    selectFile(page().querySelector('input[type="file"]') as HTMLInputElement, imageFile());
    await fillAndSubmit();

    http.expectOne(`${TEST_API_URL}/events`).flush(buildEvent());
    await harness.fixture.whenStable();
    http.expectOne(`${TEST_API_URL}/events/10/images/upload`).flush(SIGNED);
    http.expectOne(SIGNED.upload_url).flush({}, { status: 400, statusText: 'Bad Request' });
    await harness.fixture.whenStable();

    expect(TestBed.inject(Router).url).toBe('/events/10');
    const message = TestBed.inject(FlashMessageService).consume();
    expect(message?.type).toBe('error');
    expect(message?.text).toContain('No se pudo subir la imagen a Cloudinary');
    expect(message?.text).toContain('«Editar evento»');
  });
});
