import { type ComponentFixture, TestBed } from '@angular/core/testing';

import {
  buildEvent,
  fillDateTime,
  provideTestDependencies,
  textOf,
} from '../../../../../testing/test-helpers';
import { type EventUpdatePayload } from '../../models/event.model';
import { EventForm } from './event-form';

describe('EventForm', () => {
  let fixture: ComponentFixture<EventForm>;
  let element: HTMLElement;
  let emitted: EventUpdatePayload[];

  function fill(label: string, value: string): void {
    const field = [...element.querySelectorAll('app-form-field')].find((candidate) =>
      textOf(candidate.querySelector('label')).startsWith(label),
    );
    const control = field?.querySelector<HTMLInputElement | HTMLTextAreaElement>('input, textarea');
    if (!field || !control) {
      throw new Error(`Field not found: ${label}`);
    }
    if (field.querySelector('app-date-time-input')) {
      fillDateTime(field, value);
      return;
    }
    control.value = value;
    control.dispatchEvent(new Event('input'));
  }

  async function submit(): Promise<void> {
    element.querySelector<HTMLButtonElement>('button[type="submit"]')?.click();
    await fixture.whenStable();
  }

  const errors = () => [...element.querySelectorAll('.error')].map((error) => textOf(error));

  beforeEach(async () => {
    TestBed.configureTestingModule({ providers: provideTestDependencies() });
    fixture = TestBed.createComponent(EventForm);
    element = fixture.nativeElement;
    emitted = [];
    fixture.componentInstance.save.subscribe((payload) => emitted.push(payload));
    await fixture.whenStable();
  });

  it('should not emit and should show errors when required fields are missing', async () => {
    await submit();

    expect(emitted).toEqual([]);
    expect(errors()).toContain('Este campo es obligatorio.');
    const invalidFields = [...element.querySelectorAll('app-form-field')].filter((field) =>
      field.querySelector('[aria-invalid="true"]'),
    );
    expect(invalidFields.length).toBe(5);
  });

  it('should reject blank names and an end date before the start date', async () => {
    fill('Nombre', '   ');
    fill('Ubicación', 'Bogotá');
    fill('Inicio', '2030-05-10T10:00');
    fill('Finalización', '2030-05-10T09:00');
    fill('Capacidad', '10');
    await submit();

    expect(emitted).toEqual([]);
    expect(errors()).toContain('Este campo no puede estar vacío.');
    expect(errors()).toContain('La fecha de finalización debe ser posterior a la de inicio.');
  });

  it('should reject a capacity lower than 1', async () => {
    fill('Capacidad', '0');
    await submit();
    expect(errors()).toContain('La capacidad debe ser al menos 1.');
  });

  it('should emit trimmed text, the Colombian schedule in UTC and a numeric capacity', async () => {
    fill('Nombre', '  Angular Day ');
    fill('Ubicación', 'Bogotá');
    fill('Inicio', '2030-05-10T10:00');
    fill('Finalización', '2030-05-10T18:00');
    fill('Capacidad', '150');
    await submit();

    expect(emitted).toEqual([
      {
        name: 'Angular Day',
        description: null,
        location: 'Bogotá',
        start_date: '2030-05-10T15:00:00.000Z',
        end_date: '2030-05-10T23:00:00.000Z',
        capacity: 150,
      },
    ]);
  });

  it('should prefill an existing event and only send a changed status', async () => {
    fixture.componentRef.setInput('event', buildEvent({ status: 'DRAFT' }));
    await fixture.whenStable();

    const status = () => [...element.querySelectorAll('select')].at(-1)!;
    const options = [...status().options].map((option) => textOf(option));
    expect(options).toEqual(['Borrador', 'Publicado', 'Cancelado']);

    await submit();
    expect(emitted[0].name).toBe('Angular Summit');
    expect(emitted[0].status).toBeUndefined();

    const select = status();
    select.value = 'PUBLISHED';
    select.dispatchEvent(new Event('change'));
    await submit();
    expect(emitted[1].status).toBe('PUBLISHED');
  });

  it('should load the schedule of an event in Colombia time, with AM/PM', async () => {
    fixture.componentRef.setInput(
      'event',
      buildEvent({
        start_date: '2030-05-10T14:00:00+00:00',
        end_date: '2030-05-11T04:30:00+00:00',
      }),
    );
    await fixture.whenStable();

    const [start, end] = [...element.querySelectorAll('app-date-time-input')].map((field) => [
      field.querySelector('input')?.value,
      ...[...field.querySelectorAll('select')].map((select) => select.selectedOptions[0]?.text),
    ]);
    expect(start).toEqual(['2030-05-10', '9', '00', 'AM']);
    expect(end).toEqual(['2030-05-10', '11', '30', 'PM']);
    expect(textOf(element)).toContain('10/05/2030, 11:30 PM (hora de Colombia)');
  });

  it('should send back the same instants when the schedule is not edited', async () => {
    fixture.componentRef.setInput(
      'event',
      buildEvent({
        start_date: '2030-05-10T14:00:00+00:00',
        end_date: '2030-05-11T04:30:00+00:00',
      }),
    );
    await fixture.whenStable();
    await submit();

    expect(emitted[0].start_date).toBe('2030-05-10T14:00:00.000Z');
    expect(emitted[0].end_date).toBe('2030-05-11T04:30:00.000Z');
  });

  it('should focus the first invalid schedule field after a rejected submit', async () => {
    fill('Nombre', 'Angular Day');
    fill('Ubicación', 'Bogotá');
    await fixture.whenStable();
    await submit();

    expect(document.activeElement).toBe(element.querySelector('app-date-time-input input'));
  });

  it('should display field errors returned by the API', async () => {
    fixture.componentRef.setInput('serverErrors', { name: ['Longer than maximum length 200.'] });
    await fixture.whenStable();

    expect(errors()).toContain('Longer than maximum length 200.');
  });

  it('should block duplicate submissions while saving', async () => {
    fixture.componentRef.setInput('event', buildEvent());
    fixture.componentRef.setInput('submitting', true);
    await fixture.whenStable();

    const button = element.querySelector<HTMLButtonElement>('button[type="submit"]')!;
    expect(button.disabled).toBeTrue();
    expect(button.getAttribute('aria-busy')).toBe('true');
    await submit();
    expect(emitted).toEqual([]);
  });
});
