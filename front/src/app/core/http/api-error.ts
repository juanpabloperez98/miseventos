import { HttpErrorResponse } from '@angular/common/http';

export type FieldErrors = Record<string, string[]>;

export interface ApiError {
  status: number;
  serverMessage: string | null;
  fieldErrors: FieldErrors;
}

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
  'Event image not found': 'El evento no tiene imagen.',
  'Image uploads are not configured': 'La carga de imágenes no está disponible en este momento.',
  'The image service could not complete the operation':
    'El servicio de imágenes no respondió. Inténtalo de nuevo más tarde.',
  'The uploaded image could not be verified':
    'No se pudo verificar la imagen subida. Inténtalo de nuevo.',
  'The image was not uploaded for this event': 'La imagen no corresponde a este evento.',
  'The uploaded file is not an allowed image format':
    'El archivo no es una imagen JPG, PNG o WebP.',
};

export function describeApiError(error: ApiError): string {
  if (error.serverMessage && KNOWN_MESSAGES[error.serverMessage]) {
    return KNOWN_MESSAGES[error.serverMessage];
  }
  if (error.serverMessage?.startsWith('Cannot change event status')) {
    return KNOWN_MESSAGES['Invalid event status transition'];
  }
  if (error.serverMessage?.startsWith('Only these image types are allowed')) {
    return 'Solo se admiten imágenes JPG, PNG o WebP.';
  }
  if (error.serverMessage?.startsWith('The image must not exceed')) {
    return 'La imagen supera el tamaño máximo permitido.';
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
