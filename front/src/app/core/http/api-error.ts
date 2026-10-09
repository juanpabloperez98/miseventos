import { HttpErrorResponse } from '@angular/common/http';

/** Field-level validation messages, keyed by request field name (e.g. `{ email: ['...'] }`). */
export type FieldErrors = Record<string, string[]>;

/**
 * Normalized API error.
 *
 * The backend always answers errors as `{ message, errors? }`, where `errors` groups marshmallow
 * validation messages by request location: `{ json: { field: [messages] } }`.
 */
export interface ApiError {
  /** HTTP status. `0` means the server could not be reached. */
  status: number;
  /** Raw message sent by the backend, if any. */
  serverMessage: string | null;
  fieldErrors: FieldErrors;
}

/** Converts anything thrown by `HttpClient` into an {@link ApiError}. */
export function toApiError(error: unknown): ApiError {
  if (!(error instanceof HttpErrorResponse)) {
    return { status: 0, serverMessage: null, fieldErrors: {} };
  }
  const body: unknown = error.error;
  return {
    status: error.status,
    serverMessage: isRecord(body) && typeof body['message'] === 'string' ? body['message'] : null,
    fieldErrors: isRecord(body) ? collectFieldErrors(body['errors']) : {},
  };
}

/** Known backend messages translated for the user interface. */
const KNOWN_MESSAGES: Record<string, string> = {
  'Invalid email or password': 'El correo o la contraseña no son correctos.',
  'Email is already registered': 'Este correo ya está registrado.',
  'Invalid or expired token': 'Tu sesión ha expirado. Inicia sesión de nuevo.',
  'Event not found': 'El evento no existe o no está disponible.',
  'Cancelled or completed events cannot be modified':
    'Los eventos cancelados o finalizados no se pueden modificar.',
  'Only draft or published events can be removed':
    'Solo se pueden eliminar eventos en borrador o publicados.',
  'Capacity cannot be lower than the number of registered attendees':
    'La capacidad no puede ser menor que el número de personas inscritas.',
  'Start must be before end': 'La fecha de inicio debe ser anterior a la de finalización.',
  'Invalid event status transition': 'El cambio de estado no está permitido.',
  'User is already registered to this event': 'Ya estás inscrito en este evento.',
  'Event is not open for registration': 'Este evento no admite inscripciones en este momento.',
  'Event has reached its capacity': 'El evento ha alcanzado su capacidad máxima.',
  'Session must take place within the event schedule':
    'La sesión debe estar dentro del horario del evento.',
  'Speaker not found': 'El ponente seleccionado no existe.',
  'Session capacity cannot exceed the event capacity':
    'La capacidad de la sesión no puede superar la capacidad del evento.',
  'Session not found': 'La sesión no existe o no está disponible.',
};

/** Returns a user-facing message (in Spanish) describing the error. */
export function describeApiError(error: ApiError): string {
  if (error.serverMessage && KNOWN_MESSAGES[error.serverMessage]) {
    return KNOWN_MESSAGES[error.serverMessage];
  }
  if (error.serverMessage?.startsWith('Cannot change event status')) {
    return KNOWN_MESSAGES['Invalid event status transition'];
  }
  switch (error.status) {
    case 0:
      return 'No se pudo conectar con el servidor. Comprueba tu conexión e inténtalo de nuevo.';
    case 401:
      return 'Necesitas iniciar sesión para continuar.';
    case 403:
      return 'No tienes permiso para realizar esta acción.';
    case 404:
      return 'El recurso solicitado no existe o no está disponible.';
    case 409:
      return 'La operación no es compatible con el estado actual del recurso.';
    case 422:
      return 'Revisa los datos enviados.';
    default:
      return error.status >= 500
        ? 'Se produjo un error en el servidor. Inténtalo de nuevo más tarde.'
        : 'No se pudo completar la operación.';
  }
}

function collectFieldErrors(errors: unknown): FieldErrors {
  const result: FieldErrors = {};
  if (!isRecord(errors)) {
    return result;
  }
  // Merge every location (json, query...) into a single field map.
  for (const location of Object.values(errors)) {
    if (!isRecord(location)) {
      continue;
    }
    for (const [field, messages] of Object.entries(location)) {
      if (Array.isArray(messages)) {
        result[field] = messages.filter((m): m is string => typeof m === 'string');
      }
    }
  }
  return result;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
