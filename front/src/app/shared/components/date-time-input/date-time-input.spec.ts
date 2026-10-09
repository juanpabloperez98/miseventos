import { ChangeDetectionStrategy, Component } from '@angular/core';
import { type ComponentFixture, TestBed } from '@angular/core/testing';
import { FormControl, ReactiveFormsModule } from '@angular/forms';

import { fillDateTime, provideTestDependencies, textOf } from '../../../../testing/test-helpers';
import { DateTimeInput } from './date-time-input';

@Component({
  imports: [ReactiveFormsModule, DateTimeInput],
  template: `<app-date-time-input
    inputId="start"
    [formControl]="control"
    min="2026-10-10T08:00"
    max="2026-10-12T18:00"
  />`,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
class Host {
  readonly control = new FormControl('', { nonNullable: true });
}

describe('DateTimeInput', () => {
  let fixture: ComponentFixture<Host>;
  let element: HTMLElement;
  let control: FormControl<string>;

  const dateInput = () => element.querySelector('input') as HTMLInputElement;
  const selects = () => [...element.querySelectorAll('select')];
  const selected = () => selects().map((select) => select.selectedOptions[0]?.text.trim());
  const summary = () => textOf(element.querySelector('.date-time__summary'));

  beforeEach(async () => {
    TestBed.configureTestingModule({ providers: provideTestDependencies() });
    fixture = TestBed.createComponent(Host);
    element = fixture.nativeElement;
    control = fixture.componentInstance.control;
    await fixture.whenStable();
  });

  it('should offer only the 12-hour clock', () => {
    const [hour, minute, period] = selects().map((select) =>
      [...select.options].map((option) => option.text.trim()),
    );

    expect(dateInput().type).toBe('date');
    expect(dateInput().id).toBe('start');
    expect(hour).toEqual(['--', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']);
    expect(minute.length).toBe(61);
    expect(period).toEqual(['--', 'AM', 'PM']);
    expect(selects().map((select) => select.getAttribute('aria-label'))).toEqual([
      'Hora',
      'Minutos',
      'AM o PM',
    ]);
  });

  it('should limit the date picker to the dates of the bounds', () => {
    expect(dateInput().getAttribute('min')).toBe('2026-10-10');
    expect(dateInput().getAttribute('max')).toBe('2026-10-12');
  });

  it('should show a stored value in AM/PM without changing it', async () => {
    control.setValue('2026-10-10T14:30');
    await fixture.whenStable();

    expect(dateInput().value).toBe('2026-10-10');
    expect(selected()).toEqual(['2', '30', 'PM']);
    expect(summary()).toBe('10/10/2026, 2:30 PM (hora de Colombia)');
    expect(control.value).toBe('2026-10-10T14:30');
  });

  it('should show midnight and noon as 12 AM and 12 PM', async () => {
    control.setValue('2026-10-10T00:05');
    await fixture.whenStable();
    expect(selected()).toEqual(['12', '05', 'AM']);

    control.setValue('2026-10-10T12:00');
    await fixture.whenStable();
    expect(selected()).toEqual(['12', '00', 'PM']);
  });

  it('should emit the value in the 24-hour format used by the form', async () => {
    fillDateTime(element, '2026-10-10T23:45');
    await fixture.whenStable();
    expect(control.value).toBe('2026-10-10T23:45');
    expect(summary()).toBe('10/10/2026, 11:45 PM (hora de Colombia)');

    fillDateTime(element, '2026-10-11T00:15');
    await fixture.whenStable();
    expect(control.value).toBe('2026-10-11T00:15');
  });

  it('should keep the value empty until date and time are complete', async () => {
    dateInput().value = '2026-10-10';
    dateInput().dispatchEvent(new Event('input'));
    const [hour] = selects();
    hour.value = '9';
    hour.dispatchEvent(new Event('change'));
    await fixture.whenStable();

    expect(control.value).toBe('');
    expect(summary()).toBe('');
  });

  it('should clear every part when the value is reset', async () => {
    control.setValue('2026-10-10T14:30');
    await fixture.whenStable();
    control.reset();
    await fixture.whenStable();

    expect(dateInput().value).toBe('');
    expect(selected()).toEqual(['--', '--', '--']);
  });

  it('should be marked as touched when the focus leaves the group', () => {
    selects()[0].dispatchEvent(new FocusEvent('focusout', { bubbles: true, relatedTarget: null }));

    expect(control.touched).toBeTrue();
  });

  it('should disable all its parts with the control', async () => {
    control.disable();
    await fixture.whenStable();

    expect(dateInput().disabled).toBeTrue();
    expect(selects().every((select) => select.disabled)).toBeTrue();
  });
});
