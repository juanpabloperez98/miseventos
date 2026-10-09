/**
 * First invalid control of a form, to focus it after a rejected submit. Composite controls (such as
 * `app-date-time-input`) carry the `ng-invalid` class on their host, so their first input is used.
 */
export const INVALID_CONTROL_SELECTOR =
  '.ng-invalid:is(input, textarea, select), app-date-time-input.ng-invalid input';
