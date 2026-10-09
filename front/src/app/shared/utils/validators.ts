import { type AbstractControl, type ValidationErrors, type ValidatorFn } from '@angular/forms';

/** Rejects values made only of whitespace (the backend rejects blank names and locations). */
export const notBlank: ValidatorFn = (
  control: AbstractControl<unknown>,
): ValidationErrors | null =>
  typeof control.value === 'string' && control.value.length > 0 && control.value.trim() === ''
    ? { notBlank: true }
    : null;

/** Accepts only whole numbers. Empty values are left to `Validators.required`. */
export const integer: ValidatorFn = (
  control: AbstractControl<unknown>,
): ValidationErrors | null => {
  const value = control.value;
  if (value === null || value === undefined || value === '') {
    return null;
  }
  return Number.isInteger(Number(value)) ? null : { integer: true };
};

/**
 * The control must be equal to (`'same'`) or later than (`'after'`) a sibling control.
 * The sibling must call `updateValueAndValidity()` on this control when it changes.
 */
export function compareWithSibling(
  siblingName: string,
  mode: 'same' | 'after',
  errorKey: string,
): ValidatorFn {
  return (control: AbstractControl<unknown>): ValidationErrors | null => {
    const sibling: unknown = control.parent?.get(siblingName)?.value;
    const value = control.value;
    if (!value || !sibling) {
      return null;
    }
    const valid = mode === 'same' ? value === sibling : String(value) > String(sibling);
    return valid ? null : { [errorKey]: true };
  };
}
