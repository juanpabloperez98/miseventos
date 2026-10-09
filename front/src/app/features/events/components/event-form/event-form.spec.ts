import { type ComponentFixture, TestBed } from '@angular/core/testing';

import { buildEvent, provideTestDependencies, textOf } from '../../../../../testing/test-helpers';
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
    if (!control) {
      throw new Error(`Field not found: ${label}`);
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
    expect(element.querySelectorAll('[aria-invalid="true"]').length).toBe(5);
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

  it('should emit a payload with trimmed text, UTC dates and a numeric capacity', async () => {
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
        start_date: new Date('2030-05-10T10:00').toISOString(),
        end_date: new Date('2030-05-10T18:00').toISOString(),
        capacity: 150,
      },
    ]);
  });

  it('should prefill an existing event and only send a changed status', async () => {
    fixture.componentRef.setInput('event', buildEvent({ status: 'DRAFT' }));
    await fixture.whenStable();

    const options = [...element.querySelectorAll('select option')].map((option) => textOf(option));
    expect(options).toEqual(['Borrador', 'Publicado', 'Cancelado']);

    await submit();
    expect(emitted[0].name).toBe('Angular Summit');
    expect(emitted[0].status).toBeUndefined();

    const select = element.querySelector('select')!;
    select.value = 'PUBLISHED';
    select.dispatchEvent(new Event('change'));
    await submit();
    expect(emitted[1].status).toBe('PUBLISHED');
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
