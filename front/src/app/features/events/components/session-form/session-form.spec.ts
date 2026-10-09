import { type ComponentFixture, TestBed } from '@angular/core/testing';

import {
  buildEvent,
  buildSession,
  fillDateTime,
  provideTestDependencies,
  textOf,
} from '../../../../../testing/test-helpers';
import { type SessionPayload } from '../../models/session.model';
import { SessionForm } from './session-form';

/** Event from 10:00 AM to 6:00 PM in Colombia time (UTC-5), whatever the device timezone. */
const EVENT = buildEvent({
  start_date: '2030-05-10T15:00:00.000Z',
  end_date: '2030-05-10T23:00:00.000Z',
  capacity: 100,
});
const SPEAKERS = [
  { id: 1, name: 'Ada Lovelace', bio: null },
  { id: 2, name: 'Grace Hopper', bio: null },
];

describe('SessionForm', () => {
  let fixture: ComponentFixture<SessionForm>;
  let element: HTMLElement;
  let emitted: SessionPayload[];

  function field(label: string): HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement {
    const found = [...element.querySelectorAll('app-form-field')].find((candidate) =>
      textOf(candidate.querySelector('label')).startsWith(label),
    );
    const control = found?.querySelector<HTMLInputElement>('input, textarea, select');
    if (!control) {
      throw new Error(`Field not found: ${label}`);
    }
    return control;
  }

  function fill(label: string, value: string): void {
    const host = [...element.querySelectorAll('app-form-field')].find((candidate) =>
      textOf(candidate.querySelector('label')).startsWith(label),
    );
    if (host?.querySelector('app-date-time-input')) {
      fillDateTime(host, value);
      return;
    }
    const control = field(label);
    control.value = value;
    control.dispatchEvent(new Event(control instanceof HTMLSelectElement ? 'change' : 'input'));
  }

  async function submit(): Promise<void> {
    element.querySelector<HTMLButtonElement>('button[type="submit"]')?.click();
    await fixture.whenStable();
  }

  const errors = () => [...element.querySelectorAll('.error')].map((error) => textOf(error));

  beforeEach(async () => {
    TestBed.configureTestingModule({ providers: provideTestDependencies() });
    fixture = TestBed.createComponent(SessionForm);
    fixture.componentRef.setInput('event', EVENT);
    fixture.componentRef.setInput('speakers', SPEAKERS);
    element = fixture.nativeElement;
    emitted = [];
    fixture.componentInstance.save.subscribe((payload) => emitted.push(payload));
    await fixture.whenStable();
  });

  it('should require title, schedule and capacity', async () => {
    await submit();

    expect(emitted).toEqual([]);
    expect(errors().filter((message) => message === 'Este campo es obligatorio.').length).toBe(4);
  });

  it('should keep the session inside the event schedule', async () => {
    fill('Título', 'Keynote');
    fill('Inicio', '2030-05-10T09:00');
    fill('Finalización', '2030-05-10T19:00');
    fill('Capacidad', '10');
    await submit();

    expect(emitted).toEqual([]);
    expect(errors()).toEqual([
      'La sesión debe estar dentro del horario del evento.',
      'La sesión debe estar dentro del horario del evento.',
    ]);
    expect(field('Inicio').getAttribute('min')).toBe('2030-05-10');
    expect(field('Inicio').getAttribute('max')).toBe('2030-05-10');
    expect(textOf(element)).toContain('Horario del evento: 10/05/2030 · 10:00 AM – 6:00 PM');
  });

  it('should require the end to be after the start and a positive capacity', async () => {
    fill('Título', 'Keynote');
    fill('Inicio', '2030-05-10T12:00');
    fill('Finalización', '2030-05-10T11:00');
    fill('Capacidad', '0');
    await submit();

    expect(emitted).toEqual([]);
    expect(errors()).toContain('La hora de finalización debe ser posterior a la de inicio.');
    expect(errors()).toContain('La capacidad debe ser al menos 1.');
  });

  it('should list the speakers and emit the payload with the selected one', async () => {
    const options = [...(field('Ponente') as HTMLSelectElement).options].map((o) => o.text.trim());
    expect(options).toEqual(['Sin ponente', 'Ada Lovelace', 'Grace Hopper']);

    fill('Título', '  Keynote ');
    fill('Inicio', '2030-05-10T11:00');
    fill('Finalización', '2030-05-10T12:30');
    fill('Capacidad', '80');
    fill('Ponente', '2');
    await submit();

    expect(emitted).toEqual([
      {
        title: 'Keynote',
        description: null,
        // 11:00 AM and 12:30 PM in Bogotá.
        start_time: '2030-05-10T16:00:00.000Z',
        end_time: '2030-05-10T17:30:00.000Z',
        capacity: 80,
        speaker_id: 2,
      },
    ]);
  });

  it('should prefill a session and allow removing its speaker', async () => {
    const session = buildSession({
      title: 'Signals',
      // 3:00 PM to 4:00 PM in Bogotá.
      start_time: '2030-05-10T20:00:00+00:00',
      end_time: '2030-05-10T21:00:00+00:00',
      speaker_id: 1,
    });
    fixture.componentRef.setInput('session', session);
    await fixture.whenStable();

    expect(field('Título').value).toBe('Signals');
    expect(field('Inicio').value).toBe('2030-05-10');
    const startTime = element.querySelectorAll('app-date-time-input')[0].querySelectorAll('select');
    expect([...startTime].map((select) => select.selectedOptions[0]?.text)).toEqual([
      '3',
      '00',
      'PM',
    ]);
    expect(field('Ponente').value).toBe('1');

    fill('Ponente', '');
    await submit();

    expect(emitted[0].speaker_id).toBeNull();
    // Unchanged schedule: the same instants are sent back, without any shift.
    expect(emitted[0].start_time).toBe('2030-05-10T20:00:00.000Z');
    expect(emitted[0].end_time).toBe('2030-05-10T21:00:00.000Z');
    expect(emitted[0].capacity).toBe(session.capacity);
  });

  it('should show field errors returned by the API', async () => {
    fixture.componentRef.setInput('serverErrors', { capacity: ['Must be less than 1000000.'] });
    await fixture.whenStable();

    expect(errors()).toContain('Must be less than 1000000.');
  });

  describe('capacity limited by the event capacity (100)', () => {
    const submitButton = () =>
      element.querySelector<HTMLButtonElement>('button[type="submit"]') as HTMLButtonElement;

    async function fillValidExcept(capacity: string): Promise<void> {
      fill('Título', 'Keynote');
      fill('Inicio', '2030-05-10T11:00');
      fill('Finalización', '2030-05-10T12:00');
      fill('Capacidad', capacity);
      await fixture.whenStable();
    }

    it('should show the maximum allowed capacity', () => {
      const capacityField = [...element.querySelectorAll('app-form-field')].find((candidate) =>
        textOf(candidate.querySelector('label')).startsWith('Capacidad'),
      );
      expect(textOf(capacityField?.querySelector('.hint'))).toBe(
        'Máximo 100 personas (capacidad del evento).',
      );
      expect(field('Capacidad').getAttribute('max')).toBe('100');
    });

    for (const capacity of ['1', '100']) {
      it(`should accept a capacity of ${capacity}`, async () => {
        await fillValidExcept(capacity);

        expect(submitButton().disabled).toBeFalse();
        await submit();
        expect(emitted.map((payload) => payload.capacity)).toEqual([Number(capacity)]);
      });
    }

    it('should reject 101 with a clear message and disable submitting', async () => {
      await fillValidExcept('101');

      expect(errors()).toContain('La capacidad no puede superar la del evento (100 personas).');
      expect(submitButton().disabled).toBeTrue();
      await submit();
      expect(emitted).toEqual([]);
    });

    it('should disable submitting for a capacity of 0 and enable it again once fixed', async () => {
      await fillValidExcept('0');
      expect(submitButton().disabled).toBeTrue();

      fill('Capacidad', '100');
      await fixture.whenStable();

      expect(submitButton().disabled).toBeFalse();
      expect(errors()).toEqual([]);
    });

    it('should keep submitting enabled while the capacity is empty, to show required fields', () => {
      expect(submitButton().disabled).toBeFalse();
    });

    it('should flag an existing session whose capacity exceeds the event capacity', async () => {
      fixture.componentRef.setInput(
        'session',
        buildSession({
          capacity: 200,
          start_time: '2030-05-10T20:00:00+00:00',
          end_time: '2030-05-10T21:00:00+00:00',
        }),
      );
      await fixture.whenStable();

      expect(errors()).toContain('La capacidad no puede superar la del evento (100 personas).');
      expect(submitButton().disabled).toBeTrue();
    });
  });
});
