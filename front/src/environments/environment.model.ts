/** Shape shared by every environment file, so all of them must define the same keys. */
export interface Environment {
  production: boolean;
  /** Base URL of the REST API, including the `/api` prefix. */
  apiUrl: string;
}
