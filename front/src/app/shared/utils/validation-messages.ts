import { type ValidationErrors } from '@angular/forms';

type MessageFactory = (detail: unknown) => string;

const DEFAULT_MESSAGES: Record<string, MessageFactory> = {
  required: () => 'Este campo es obligatorio.',
  notBlank: () => 'Este campo no puede estar vacío.',
  email: () => 'Introduce un correo electrónico válido.',
  minlength: (detail) => `Debe tener al menos ${lengthOf(detail, 'requiredLength')} caracteres.`,
  maxlength: (detail) => `Debe tener como máximo ${lengthOf(detail, 'requiredLength')} caracteres.`,
  min: (detail) => `El valor mínimo es ${lengthOf(detail, 'min')}.`,
  max: (detail) => `El valor máximo es ${lengthOf(detail, 'max')}.`,
  integer: () => 'Introduce un número entero.',
  server: (detail) => (typeof detail === 'string' ? detail : 'Valor no válido.'),
};

export function validationMessage(
  errors: ValidationErrors | null,
  overrides: Record<string, string> = {},
): string | null {
  if (!errors) {
    return null;
  }
  const [key, detail] = Object.entries(errors)[0] ?? [];
  if (key === undefined) {
    return null;
  }
  if (overrides[key]) {
    return overrides[key];
  }
  return DEFAULT_MESSAGES[key]?.(detail) ?? 'Valor no válido.';
}

function lengthOf(detail: unknown, property: string): string {
  if (typeof detail === 'object' && detail !== null && property in detail) {
    return String((detail as Record<string, unknown>)[property]);
  }
  return '';
}
